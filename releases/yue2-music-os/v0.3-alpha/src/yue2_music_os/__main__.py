from __future__ import annotations

import argparse
import io
import json
import sys
import time

import uvicorn

from .api import create_app
from .config import ConfigurationError, Settings
from .models import GenerateRequest, JobStatus
from .sample_data import SAMPLE_LYRICS, SAMPLE_SCORE, SAMPLE_STYLE
from .service import MusicService
from .storage import Store


def _is_loopback(host: str) -> bool:
    return host in {"127.0.0.1", "::1", "localhost"}


def command_serve(args: argparse.Namespace, settings: Settings) -> int:
    if not _is_loopback(args.host) and not settings.api_token and not args.insecure_no_auth:
        raise ConfigurationError(
            "refusing a non-loopback bind without YUE2_MUSIC_OS_API_TOKEN; "
            "set a token or pass --insecure-no-auth explicitly"
        )
    uvicorn.run(
        create_app(settings),
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )
    return 0


def command_doctor(_args: argparse.Namespace, settings: Settings) -> int:
    service = MusicService(settings, enforce_single_instance=False)
    try:
        payload = service.doctor()
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        engine = payload["engine"]
        return 0 if isinstance(engine, dict) and engine.get("ready") else 1
    finally:
        service.close()


def command_init_demo(args: argparse.Namespace, settings: Settings) -> int:
    store = Store(settings.data_dir)
    project = store.create_project(args.name)
    score = store.save_upload(
        project.id,
        "demo-score.abc",
        io.BytesIO(SAMPLE_SCORE.encode("utf-8")),
        settings.max_upload_bytes,
        "text/vnd.abc",
    )
    result: dict[str, object] = {
        "project": project.model_dump(mode="json"),
        "score": score.model_dump(mode="json"),
    }
    if settings.engine == "mock" and args.generate:
        service = MusicService(settings, store=store)
        try:
            job = service.submit_generate(
                GenerateRequest(
                    project_id=project.id,
                    style=SAMPLE_STYLE,
                    lyrics=SAMPLE_LYRICS,
                    cot="full",
                    seed=42,
                    abc_artifact_id=score.id,
                    candidate_count=2,
                )
            )
            deadline = time.monotonic() + args.timeout
            while True:
                current = store.get_job(job.id)
                if current.status in {JobStatus.SUCCEEDED, JobStatus.FAILED}:
                    result["job"] = current.model_dump(mode="json")
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"demo job {job.id} did not finish")
                time.sleep(0.05)
        finally:
            service.close()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yue2-music-os",
        description="Score-first controller and verification layer for YuE2/SheetSage2",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="run the local web controller")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    serve.add_argument("--log-level", default="info")
    serve.add_argument(
        "--insecure-no-auth",
        action="store_true",
        help="allow a non-loopback bind without an API token (not recommended)",
    )

    sub.add_parser("doctor", help="print readiness and model-use policy")

    demo = sub.add_parser("init-demo", help="create a demo project and sample score")
    demo.add_argument("--name", default="YuE2 Music OS Demo")
    demo.add_argument("--generate", action=argparse.BooleanOptionalAction, default=True)
    demo.add_argument("--timeout", type=float, default=30.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env()
        if args.command == "serve":
            return command_serve(args, settings)
        if args.command == "doctor":
            return command_doctor(args, settings)
        if args.command == "init-demo":
            return command_init_demo(args, settings)
        parser.error(f"unknown command {args.command}")
    except (ConfigurationError, OSError, ValueError, TimeoutError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
