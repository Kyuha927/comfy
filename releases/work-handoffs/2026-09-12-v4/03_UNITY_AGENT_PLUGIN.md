# ONE-SHOT WORK HANDOFF — Unity Agent Plugin

## Model routing
- MAIN owner: **GPT-5.6 Sol — XHigh**
- Unity/editor implementation: **GPT-5.6 Sol — High**
- Gameplay/visual/system reviewer: **GPT-6 Astra — High; XHigh for unresolved structural failures**
- Automated journey/regression tests: **GPT-5.6 Terra — High**
- Package/log/repository inventory: **GPT-5.6 Luna — Medium**
- No Pro model/profile in Work.

Continue the direct development around Unity-Technologies/unity-agent-plugin and the broader Unity automation stack. The objective is an AI that can reliably inspect, modify, run, interact with, observe, and verify a Unity project, not merely generate scripts.

Recover current project state and prior implementation first. Prioritize hierarchy/component inspection, asset operations, code editing, compilation/error capture, package/version compatibility, play-mode control, Input System interaction, automated gameplay journeys, screenshots/frame evidence, logs/exceptions, instrumentation, deterministic success criteria, safe mutation/rollback, and long-running job handling.

Treat the official Unity plugin as an input, not unquestioned architecture. Run a representative real path when available: change/create → compile → enter play mode → interact → observe → verify. Repair failures discovered there.

Sol implements. Terra owns repeatable gameplay and regression journeys. Luna gathers bounded package/log information. Astra judges cross-system/visual failures and performs the final system audit.

Do not stop at a design document. Final output must show implemented capabilities, real tested workflows, failures fixed, evidence, unresolved external blockers, and readiness for autonomous game-development work.