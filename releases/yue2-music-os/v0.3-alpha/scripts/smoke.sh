#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${PYTHON:-}" ]]; then
  PYTHON_BIN="$PYTHON"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi
PORT="${PORT:-8877}"
TMP="$(mktemp -d)"
LOG="$TMP/server.log"
PID=""
cleanup() {
  if [[ -n "$PID" ]]; then kill "$PID" >/dev/null 2>&1 || true; wait "$PID" 2>/dev/null || true; fi
  rm -rf "$TMP"
}
trap cleanup EXIT

export YUE2_MUSIC_OS_ENGINE=mock
export YUE2_MUSIC_OS_DATA="$TMP/data"
export YUE2_MUSIC_OS_API_TOKEN="smoke-token"

"$PYTHON_BIN" -m yue2_music_os serve --host 127.0.0.1 --port "$PORT" >"$LOG" 2>&1 &
PID=$!
AUTH=(-H 'X-Music-OS-Token: smoke-token')
JSON=(-H 'Content-Type: application/json')

for _ in $(seq 1 80); do
  if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then break; fi
  sleep 0.1
done
curl -fsS "http://127.0.0.1:$PORT/api/health" | "$PYTHON_BIN" -m json.tool >/dev/null
curl -fsS "http://127.0.0.1:$PORT/api/render-providers" "${AUTH[@]}" | \
  "$PYTHON_BIN" -c 'import json,sys; assert any(x["id"]=="flow-lyria-manual" for x in json.load(sys.stdin))'

wait_job() {
  local job_id="$1" status="queued" body=""
  for _ in $(seq 1 120); do
    body="$(curl -fsS "http://127.0.0.1:$PORT/api/jobs/$job_id" "${AUTH[@]}")"
    status="$(printf '%s' "$body" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
    [[ "$status" == "succeeded" || "$status" == "failed" ]] && break
    sleep 0.1
  done
  [[ "$status" == "succeeded" ]] || { echo "Smoke job $job_id ended as $status" >&2; printf '%s\n' "$body" >&2; cat "$LOG" >&2; exit 1; }
  printf '%s' "$body"
}

PROJECT_JSON="$(curl -fsS -X POST "http://127.0.0.1:$PORT/api/projects" \
  "${JSON[@]}" "${AUTH[@]}" -d '{"name":"Smoke Project"}')"
PROJECT_ID="$(printf '%s' "$PROJECT_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

curl -fsS -X POST "http://127.0.0.1:$PORT/api/projects/$PROJECT_ID/uploads" \
  "${AUTH[@]}" -F "file=@$ROOT/examples/score.abc" >/dev/null
ARTIFACT_ID="$(curl -fsS "http://127.0.0.1:$PORT/api/projects/$PROJECT_ID/artifacts" \
  "${AUTH[@]}" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')"

GENERATE_JSON="$(curl -fsS -X POST "http://127.0.0.1:$PORT/api/jobs/generate" \
  "${JSON[@]}" "${AUTH[@]}" \
  -d "{\"project_id\":\"$PROJECT_ID\",\"style\":\"Korean piano pop\",\"lyrics\":\"[Verse]\\n테스트 노래\",\"cot\":\"full\",\"seed\":42,\"candidate_count\":2,\"abc_artifact_id\":\"$ARTIFACT_ID\"}")"
GENERATE_ID="$(printf '%s' "$GENERATE_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
wait_job "$GENERATE_ID" >/dev/null

RANK_JSON="$(curl -fsS -X POST "http://127.0.0.1:$PORT/api/jobs/rank-candidates" \
  "${JSON[@]}" "${AUTH[@]}" \
  -d "{\"project_id\":\"$PROJECT_ID\",\"generation_job_id\":\"$GENERATE_ID\"}")"
RANK_ID="$(printf '%s' "$RANK_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
RANK_DONE="$(wait_job "$RANK_ID")"
printf '%s' "$RANK_DONE" | "$PYTHON_BIN" -c 'import json,sys; r=json.load(sys.stdin)["result"]; assert r["quality_claim"] is False; assert r["recommended_candidate"]==1'

PRODUCTION_JSON="$(curl -fsS -X POST "http://127.0.0.1:$PORT/api/jobs/production-render" \
  "${JSON[@]}" "${AUTH[@]}" \
  -d "{\"project_id\":\"$PROJECT_ID\",\"generation_job_id\":\"$GENERATE_ID\",\"candidate\":\"best-technical\",\"provider_ids\":[\"flow-lyria-manual\"],\"title\":\"Smoke production\",\"commercial_intent\":true,\"license_review_acknowledged\":true}")"
PRODUCTION_ID="$(printf '%s' "$PRODUCTION_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
PRODUCTION_DONE="$(wait_job "$PRODUCTION_ID")"
printf '%s' "$PRODUCTION_DONE" | "$PYTHON_BIN" -c 'import json,sys; r=json.load(sys.stdin)["result"]; assert r["source_audio_in_provider_packages"] is False; assert r["provider_receipts"][0]["status"]=="exported"'

ARTIFACTS="$(curl -fsS "http://127.0.0.1:$PORT/api/projects/$PROJECT_ID/artifacts" "${AUTH[@]}")"
AUDIO_COUNT="$(printf '%s' "$ARTIFACTS" | "$PYTHON_BIN" -c 'import json,sys; print(sum(x["kind"]=="audio" for x in json.load(sys.stdin)))')"
MANIFEST_COUNT="$(printf '%s' "$ARTIFACTS" | "$PYTHON_BIN" -c 'import json,sys; print(sum("production-manifest.json" in x["name"] for x in json.load(sys.stdin)))')"
[[ "$AUDIO_COUNT" -eq 3 ]] || { echo "Expected two candidate audio artifacts plus one audit copy, got $AUDIO_COUNT" >&2; exit 1; }
[[ "$MANIFEST_COUNT" -eq 1 ]] || { echo "Expected one production manifest, got $MANIFEST_COUNT" >&2; exit 1; }

echo "SMOKE PASS project=$PROJECT_ID generate=$GENERATE_ID rank=$RANK_ID production=$PRODUCTION_ID"
