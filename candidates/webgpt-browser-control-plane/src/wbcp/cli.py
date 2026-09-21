from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .evidence import EvidenceLedger
from .mock_browser import MockBrowserAdapter
from .models import ActionRequest, ApprovalKind, RiskTier
from .orchestrator import JobOrchestrator
from .permits import ApprovalAuthority, PermitAuthority, PermitRegistry
from .policy import PolicyConfig, PolicyEngine
from .store import JobStore
from .url_guard import URLGuard, URLPolicy
from .mcp_protocol import McpProtocolServer
from .mcp_transport import HttpTransportConfig, McpHttpTransport, run_stdio
from .runtime import BrowserControlRuntime, build_runtime
from .settings import RuntimeConfigurationError, RuntimeSettings
from .checkpoints import generate_keypair, sign_ledger_checkpoint, verify_checkpoint


def _build_demo(root: Path, host: str) -> tuple[JobOrchestrator, PermitAuthority, ApprovalAuthority, EvidenceLedger]:
    registry = PermitRegistry(str(root / "permits.sqlite3"))
    permits = PermitAuthority(b"P" * 32, registry)
    approvals = ApprovalAuthority(b"A" * 32, registry)
    evidence = EvidenceLedger(root / "evidence.jsonl", hmac_key=b"E" * 32)
    orchestrator = JobOrchestrator(
        url_guard=URLGuard(URLPolicy(allowed_hosts={host})),
        policy=PolicyEngine(PolicyConfig()),
        permits=permits,
        approvals=approvals,
        store=JobStore(str(root / "jobs.sqlite3")),
        evidence=evidence,
        host_subject="demo-attested-host",
    )
    return orchestrator, permits, approvals, evidence


def cmd_doctor(_: argparse.Namespace) -> int:
    status = {
        "component": "WebGPT Browser Control Plane",
        "status": "OFFLINE_TESTED_CANDIDATE",
        "production_ready": False,
        "live_playwright_verified": False,
        "chatgpt_roundtrip_verified": False,
        "official_route_reconciled": True,
        "hard_blockers": [
            "real ChatGPT MCP/plugin roundtrip not run",
            "real browser/site acceptance not run",
            "production identity and key management not configured",
            "user production promotion not granted",
        ],
    }
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


def cmd_verify_evidence(args: argparse.Namespace) -> int:
    key = bytes.fromhex(args.hmac_key_hex)
    ledger = EvidenceLedger(args.path, hmac_key=key)
    result = ledger.verify()
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.valid else 2


def cmd_simulate(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        host = args.host
        orchestrator, permits, approvals, evidence = _build_demo(root, host)
        request = ActionRequest(
            session_id="demo-session",
            idempotency_key=args.idempotency_key,
            action_type=args.action,
            target_url=f"https://{host}{args.path}",
            payload=json.loads(args.payload),
            expected=json.loads(args.expected),
            estimated_cost=args.cost,
            currency="USD" if args.cost is not None else None,
        )
        preflight = orchestrator.preflight(request)
        if preflight.job.state.value == "BLOCKED":
            print(json.dumps(preflight.job.to_dict(), indent=2, sort_keys=True))
            return 3
        risk = preflight.job.risk
        permit = permits.issue(
            subject="demo-attested-host",
            session_id=request.session_id,
            allowed_actions=[request.action_type],
            exact_hosts=[host],
            risk_ceiling=risk,
            max_calls=1,
            max_cost=float(args.cost or 0.0),
            currency="USD",
        )
        approval = None
        if preflight.job.decision.approval_kind in {
            ApprovalKind.HIGH_IMPACT,
            ApprovalKind.DUAL_CONTROL,
        }:
            approvers = ["demo-owner"]
            if preflight.job.decision.approval_kind == ApprovalKind.DUAL_CONTROL:
                approvers.append("demo-security-reviewer")
            approval = approvals.issue(
                job_id=preflight.job.job_id,
                action_digest=preflight.job.decision.action_digest,
                approval_kind=preflight.job.decision.approval_kind,
                approvers=approvers,
            )
        orchestrator.authorize(
            preflight.job.job_id, permit_token=permit, approval_token=approval
        )
        browser = MockBrowserAdapter(initial_url=f"https://{host}/")
        receipt = orchestrator.run(preflight.job.job_id, browser)
        output = {
            "receipt": receipt.to_dict(),
            "evidence": evidence.verify().to_dict(),
        }
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0 if receipt.state.value == "SUCCEEDED" else 4



def _build_live_runtime(*, require_http_token: bool = False) -> BrowserControlRuntime:
    settings = RuntimeSettings.from_env(require_http_token=require_http_token)
    return BrowserControlRuntime(build_runtime(settings))


def cmd_serve_stdio(_: argparse.Namespace) -> int:
    runtime = _build_live_runtime()
    try:
        return run_stdio(McpProtocolServer(runtime))
    finally:
        runtime.close()


def cmd_serve_http(args: argparse.Namespace) -> int:
    runtime = _build_live_runtime(require_http_token=True)
    try:
        settings = runtime.components.settings
        transport = McpHttpTransport(
            McpProtocolServer(runtime),
            HttpTransportConfig(
                bearer_token=str(settings.http_bearer_token),
                allowed_origins=settings.http_allowed_origins,
                allowed_hosts=settings.http_allowed_hosts,
                require_origin=settings.http_require_origin,
                max_request_bytes=settings.http_max_request_bytes,
                max_batch_items=settings.http_max_batch_items,
                principal_id=settings.http_principal_id,
                allowed_tools=settings.http_allowed_tools,
                requests_per_minute=settings.http_requests_per_minute,
                max_concurrent_requests=settings.http_max_concurrent_requests,
            ),
        )
        try:
            import uvicorn
        except ImportError as exc:
            raise RuntimeError("Install the wbcp http extra before serving HTTP") from exc
        uvicorn.run(
            transport.app(),
            host=args.bind,
            port=args.port,
            log_level=args.log_level,
            access_log=False,
        )
        return 0
    finally:
        runtime.close()


def cmd_issue_permit(args: argparse.Namespace) -> int:
    runtime = _build_live_runtime()
    try:
        result = runtime.issue_permit(
            {
                "session_id": args.session_id,
                "allowed_actions": args.actions,
                "exact_hosts": args.hosts,
                "risk_ceiling": args.risk_ceiling,
                "max_calls": args.max_calls,
                "max_cost": args.max_cost,
                "currency": args.currency,
                "ttl_seconds": args.ttl_seconds,
            }
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    finally:
        runtime.close()


def cmd_issue_approval(args: argparse.Namespace) -> int:
    runtime = _build_live_runtime()
    try:
        result = runtime.issue_approval(
            {
                "job_id": args.job_id,
                "approval_kind": args.approval_kind,
                "approvers": args.approvers,
                "ttl_seconds": args.ttl_seconds,
                "confirm_action_digest": args.confirm_action_digest,
                "confirm_page_revision": args.confirm_page_revision,
            }
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    finally:
        runtime.close()



def cmd_generate_checkpoint_key(args: argparse.Namespace) -> int:
    result = generate_keypair(args.private_key, args.public_key)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_sign_checkpoint(args: argparse.Namespace) -> int:
    runtime = _build_live_runtime()
    try:
        result = sign_ledger_checkpoint(
            runtime.components.evidence,
            private_key_path=args.private_key,
            output_path=args.output,
            instance_id=args.instance_id,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    finally:
        runtime.close()


def cmd_verify_checkpoint(args: argparse.Namespace) -> int:
    result = verify_checkpoint(args.checkpoint, public_key_path=args.public_key)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("valid") else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wbcp")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="Show candidate readiness without overclaiming")
    doctor.set_defaults(func=cmd_doctor)

    verify = sub.add_parser("verify-evidence", help="Verify a hash-chained evidence ledger")
    verify.add_argument("path")
    verify.add_argument("--hmac-key-hex", required=True)
    verify.set_defaults(func=cmd_verify_evidence)

    sim = sub.add_parser("simulate", help="Run an offline deterministic action journey")
    sim.add_argument("--action", default="inspect")
    sim.add_argument("--host", default="example.com")
    sim.add_argument("--path", default="/")
    sim.add_argument("--idempotency-key", default="demo-1")
    sim.add_argument("--payload", default="{}")
    sim.add_argument("--expected", default='{"text_contains":"ready"}')
    sim.add_argument("--cost", type=float)
    sim.set_defaults(func=cmd_simulate)

    stdio = sub.add_parser("serve-stdio", help="Serve typed MCP JSON-RPC over stdio")
    stdio.set_defaults(func=cmd_serve_stdio)

    http = sub.add_parser("serve-http", help="Serve authenticated MCP Streamable HTTP")
    http.add_argument("--bind", default="127.0.0.1")
    http.add_argument("--port", type=int, default=8765)
    http.add_argument("--log-level", default="warning")
    http.set_defaults(func=cmd_serve_http)

    permit = sub.add_parser("issue-permit", help="Operator-only finite permit issuance")
    permit.add_argument("--session-id", required=True)
    permit.add_argument("--actions", nargs="+", required=True)
    permit.add_argument("--hosts", nargs="+", required=True)
    permit.add_argument("--risk-ceiling", type=int, choices=range(0, 5), required=True)
    permit.add_argument("--max-calls", type=int, default=1)
    permit.add_argument("--max-cost", type=float, default=0.0)
    permit.add_argument("--currency", default="USD")
    permit.add_argument("--ttl-seconds", type=int, default=300)
    permit.set_defaults(func=cmd_issue_permit)

    approval = sub.add_parser("issue-approval", help="Operator-only one-shot approval issuance")
    approval.add_argument("--job-id", required=True)
    approval.add_argument(
        "--approval-kind", choices=["HIGH_IMPACT", "DUAL_CONTROL"], required=True
    )
    approval.add_argument("--approvers", nargs="+", required=True)
    approval.add_argument("--confirm-action-digest", required=True)
    approval.add_argument("--confirm-page-revision")
    approval.add_argument("--ttl-seconds", type=int, default=120)
    approval.set_defaults(func=cmd_issue_approval)

    keygen = sub.add_parser("generate-checkpoint-key", help="Generate a local Ed25519 evidence checkpoint keypair")
    keygen.add_argument("--private-key", required=True)
    keygen.add_argument("--public-key", required=True)
    keygen.set_defaults(func=cmd_generate_checkpoint_key)

    sign = sub.add_parser("sign-checkpoint", help="Sign the current evidence root with an Ed25519 key")
    sign.add_argument("--private-key", required=True)
    sign.add_argument("--output", required=True)
    sign.add_argument("--instance-id", required=True)
    sign.set_defaults(func=cmd_sign_checkpoint)

    verify_checkpoint_parser = sub.add_parser("verify-checkpoint", help="Verify a signed evidence checkpoint")
    verify_checkpoint_parser.add_argument("--checkpoint", required=True)
    verify_checkpoint_parser.add_argument("--public-key")
    verify_checkpoint_parser.set_defaults(func=cmd_verify_checkpoint)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.func(args))
    except RuntimeConfigurationError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, sort_keys=True))
        return 78


if __name__ == "__main__":
    raise SystemExit(main())
