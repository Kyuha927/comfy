from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from yue2_music_os.engines import EngineError, LocalEngine, MockEngine


def test_mock_melody_mode_creates_chord_free_score(settings, tmp_path: Path) -> None:
    result = MockEngine(settings).generate(
        job_dir=tmp_path,
        style="test",
        lyrics="[Verse]\ntest",
        cot="melody",
        seed=1,
        candidate_count=1,
        abc_path=None,
    )
    assert result["candidate_count"] == 1
    score = (tmp_path / "output" / "candidate-01" / "score.abc").read_text()
    assert '"C"' not in score


def test_local_doctor_has_independent_lanes(settings, tmp_path: Path) -> None:
    repo = tmp_path / "YuE"
    helpers = repo / "skills" / "yue2-music" / "scripts"
    helpers.mkdir(parents=True)
    (helpers / "run_yue2.py").write_text("# helper")
    yue_python = tmp_path / "yue-python"
    yue_python.write_text("")
    local = replace(
        settings,
        engine="local",
        yue2_repo=repo,
        yue2_python=yue_python,
        sheetsage2_python=tmp_path / "missing-sheet-python",
    )
    doctor = LocalEngine(local).doctor()
    assert doctor["yue2_ready"] is True
    assert doctor["sheetsage2_ready"] is False
    assert doctor["ready"] is False


def test_local_engine_executes_reviewed_helper_contract(settings, tmp_path: Path) -> None:
    import sys

    from yue2_music_os.sample_data import SAMPLE_SCORE

    repo = tmp_path / "YuE"
    helpers = repo / "skills" / "yue2-music" / "scripts"
    helpers.mkdir(parents=True)
    run_helper = """import json
import pathlib
import sys
args = sys.argv[1:]
out = pathlib.Path(args[args.index('--output') + 1])
out.mkdir(parents=True)
(out / 'run.json').write_text(json.dumps({'results': [{'status': 'complete'}]}))
(out / 'audio.flac').write_bytes(b'fLaC')
"""
    transcribe_helper = f"""import json
import pathlib
import sys
args = sys.argv[1:]
out = pathlib.Path(args[args.index('--output') + 1])
out.mkdir(parents=True)
(out / 'score.abc').write_text({SAMPLE_SCORE!r})
(out / 'transcription_manifest.json').write_text(json.dumps({{'status': 'complete'}}))
"""
    (helpers / "run_yue2.py").write_text(run_helper, encoding="utf-8")
    (helpers / "transcribe.py").write_text(transcribe_helper, encoding="utf-8")
    source = tmp_path / "source.wav"
    source.write_bytes(b"RIFFstub")
    local_settings = replace(
        settings,
        engine="local",
        yue2_repo=repo,
        yue2_python=Path(sys.executable),
        sheetsage2_python=Path(sys.executable),
    )
    engine = LocalEngine(local_settings)
    generated_dir = tmp_path / "generate-job"
    generated_dir.mkdir()
    generated = engine.generate(
        job_dir=generated_dir,
        style="test",
        lyrics="test",
        cot="full",
        seed=7,
        candidate_count=1,
        abc_path=None,
    )
    assert generated["engine"] == "local-yue2"
    assert generated["candidates"][0]["returncode"] == 0

    transcribe_dir = tmp_path / "transcribe-job"
    transcribe_dir.mkdir()
    transcribed = engine.transcribe(
        job_dir=transcribe_dir,
        source_path=source,
        melody_only=True,
    )
    assert transcribed["engine"] == "local-sheetsage2"
    assert (transcribe_dir / "output" / "score.abc").is_file()



def _local_engine_with_run_helper(settings, tmp_path: Path, helper_source: str) -> LocalEngine:
    import sys

    repo = tmp_path / "strict-YuE"
    helpers = repo / "skills" / "yue2-music" / "scripts"
    helpers.mkdir(parents=True)
    (helpers / "run_yue2.py").write_text(helper_source, encoding="utf-8")
    return LocalEngine(
        replace(
            settings,
            engine="local",
            yue2_repo=repo,
            yue2_python=Path(sys.executable),
        )
    )


def test_local_generation_rejects_zero_exit_without_audio(settings, tmp_path: Path) -> None:
    helper = """import json
import pathlib
import sys
args = sys.argv[1:]
out = pathlib.Path(args[args.index('--output') + 1])
out.mkdir(parents=True)
(out / 'run.json').write_text(json.dumps({'results': [{'status': 'complete'}]}))
"""
    engine = _local_engine_with_run_helper(settings, tmp_path, helper)
    job_dir = tmp_path / "missing-audio-job"
    job_dir.mkdir()
    with pytest.raises(EngineError, match="audio.flac"):
        engine.generate(
            job_dir=job_dir,
            style="test",
            lyrics="test",
            cot="full",
            seed=1,
            candidate_count=1,
            abc_path=None,
        )


def test_local_generation_preserves_needs_review_status(settings, tmp_path: Path) -> None:
    helper = """import json
import pathlib
import sys
args = sys.argv[1:]
out = pathlib.Path(args[args.index('--output') + 1])
out.mkdir(parents=True)
(out / 'run.json').write_text(json.dumps({'results': [{'status': 'needs_review', 'truncated': {'semantic': True}}]}))
(out / 'audio.flac').write_bytes(b'fLaC')
raise SystemExit(1)
"""
    engine = _local_engine_with_run_helper(settings, tmp_path, helper)
    job_dir = tmp_path / "review-job"
    job_dir.mkdir()
    result = engine.generate(
        job_dir=job_dir,
        style="test",
        lyrics="test",
        cot="full",
        seed=1,
        candidate_count=1,
        abc_path=None,
    )
    assert result["review_required"] is True
    assert result["candidates"][0]["status"] == "needs_review"


def test_run_command_streams_logs_and_keeps_tails(tmp_path: Path) -> None:
    import sys

    from yue2_music_os.engines import run_command

    script = tmp_path / "logs.py"
    script.write_text(
        "import sys\nprint('hello-out')\nprint('hello-err', file=sys.stderr)\n",
        encoding="utf-8",
    )
    prefix = tmp_path / "run"
    result = run_command(
        [sys.executable, str(script)],
        cwd=tmp_path,
        timeout_seconds=5,
        log_prefix=prefix,
    )
    assert result.returncode == 0
    assert "hello-out" in result.stdout
    assert "hello-err" in result.stderr
    assert prefix.with_suffix(".stdout.log").read_text().strip() == "hello-out"
    assert prefix.with_suffix(".stderr.log").read_text().strip() == "hello-err"


def test_run_command_timeout_records_result_and_terminates_group(tmp_path: Path) -> None:
    import json
    import sys

    from yue2_music_os.engines import run_command

    script = tmp_path / "sleep.py"
    script.write_text("import time\nprint('started', flush=True)\ntime.sleep(30)\n")
    prefix = tmp_path / "timeout"
    with pytest.raises(EngineError, match="timed out"):
        run_command(
            [sys.executable, str(script)],
            cwd=tmp_path,
            timeout_seconds=1,
            log_prefix=prefix,
        )
    receipt = json.loads(prefix.with_suffix(".result.json").read_text())
    assert receipt["timed_out"] is True
    assert "started" in prefix.with_suffix(".stdout.log").read_text()
