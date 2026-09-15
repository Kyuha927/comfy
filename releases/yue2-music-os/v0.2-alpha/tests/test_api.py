from __future__ import annotations

import time

from fastapi.testclient import TestClient

from yue2_music_os.api import create_app


def wait_job(client: TestClient, job_id: str, headers: dict[str, str]) -> dict:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}", headers=headers).json()
        if job["status"] in {"succeeded", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError("job timed out")


def test_health_ui_and_authenticated_workflow(settings, tmp_path) -> None:
    protected = settings.__class__(
        **{
            **{
                field: getattr(settings, field)
                for field in settings.__dataclass_fields__
            },
            "api_token": "secret",
        }
    )
    with TestClient(create_app(protected)) as client:
        assert client.get("/").status_code == 200
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["doctor"]["engine"]["engine"] == "mock"
        assert health.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in health.headers["content-security-policy"]
        unauthorized = client.get("/api/projects")
        assert unauthorized.status_code == 401
        assert unauthorized.headers["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in unauthorized.headers["content-security-policy"]

        auth = {"X-Music-OS-Token": "secret"}
        project = client.post("/api/projects", headers=auth, json={"name": "API"})
        assert project.status_code == 201
        project_id = project.json()["id"]
        score_path = tmp_path / "score.abc"
        from yue2_music_os.sample_data import SAMPLE_SCORE

        score_path.write_text(SAMPLE_SCORE)
        uploaded = client.post(
            f"/api/projects/{project_id}/uploads",
            headers=auth,
            files={"file": ("score.abc", score_path.read_bytes(), "text/vnd.abc")},
        )
        assert uploaded.status_code == 201
        score_id = uploaded.json()["id"]

        submitted = client.post(
            "/api/jobs/generate",
            headers=auth,
            json={
                "project_id": project_id,
                "style": "Korean piano pop",
                "lyrics": "[Verse]\n테스트",
                "cot": "full",
                "seed": 5,
                "candidate_count": 1,
                "abc_artifact_id": score_id,
            },
        )
        assert submitted.status_code == 202
        done = wait_job(client, submitted.json()["id"], auth)
        assert done["status"] == "succeeded"
        artifacts = client.get(
            f"/api/projects/{project_id}/artifacts", headers=auth
        ).json()
        audio = next(item for item in artifacts if item["kind"] == "audio")
        downloaded = client.get(audio["download_url"], headers=auth)
        assert downloaded.status_code == 200
        assert downloaded.content[:4] == b"RIFF"


def test_cross_field_validation_rejects_score_with_off(settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/jobs/generate",
            json={
                "project_id": "0" * 32,
                "style": "test",
                "lyrics": "test",
                "cot": "off",
                "abc_artifact_id": "1" * 32,
            },
        )
        assert response.status_code == 422


def test_invalid_uploaded_abc_is_a_client_error(settings) -> None:
    with TestClient(create_app(settings)) as client:
        project_id = client.post("/api/projects", json={"name": "Bad score"}).json()["id"]
        uploaded = client.post(
            f"/api/projects/{project_id}/uploads",
            files={"file": ("broken.abc", b"not abc", "text/vnd.abc")},
        )
        assert uploaded.status_code == 201
        response = client.post(
            "/api/jobs/generate",
            json={
                "project_id": project_id,
                "style": "test",
                "lyrics": "test",
                "cot": "full",
                "abc_artifact_id": uploaded.json()["id"],
            },
        )
        assert response.status_code == 400
        assert "ABC" in response.json()["detail"]


def test_untrusted_host_is_rejected(settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/health", headers={"Host": "attacker.example"})
        assert response.status_code == 400
        assert "Invalid host header" in response.text
