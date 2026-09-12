# ONE-SHOT WORK HANDOFF — OpenCode CLI ↔ WebGPT Plugin

## Model routing
- MAIN owner: **GPT-5.6 Sol — XHigh**
- Core implementation/debug worker: **GPT-5.6 Sol — High**
- Security/architecture/final audit: **GPT-6 Astra — XHigh**
- Integration and fault-test worker: **GPT-5.6 Terra — High**
- Log/output classification worker: **GPT-5.6 Luna — Medium**
- Never use Pro in Work.

Take ownership of the existing effort to let WebGPT/ChatGPT use OpenCode CLI through a production-grade local plugin/bridge. Recover current code and decisions first; do not restart blindly.

Target commercial-grade behavior: explicit authorization boundary, working-directory isolation, command/job lifecycle, structured arguments, stdout/stderr streaming, cancellation, timeouts, reconnect/restart recovery, large-output handling, concurrency without cross-talk, environment control, capability detection, audit logs, stable error propagation, safe defaults, and usable ChatGPT-facing UX.

Test real normal and hostile paths: successful commands, non-zero exits, unavailable executables, malformed input, cancellation, timeout, huge stdout/stderr, Unicode/path quoting, concurrent sessions, process restart, permission failures, and repository workflows. End-to-end tests must travel through the same bridge path WebGPT uses.

Sol owns implementation. Terra builds repeatable integration/failure tests. Luna performs bounded log/inventory work only. Astra independently reviews security, architecture, privilege boundaries, unsafe command exposure, and commercial readiness after implementation.

Do not claim success from unit tests alone. Continue until the strongest feasible working version is implemented and verified. Final verdict must be PASS / CONDITIONAL PASS / FAIL with concrete evidence and any truly external blocker.