# ChatGPT Work One-Shot Handoffs v4

Corrected 2026-09-12 handoff pack.

## Hard routing rules
- Work models only: **GPT-6 Astra / GPT-5.6 Sol / GPT-5.6 Terra / GPT-5.6 Luna**.
- **Never route to any Pro model/profile in Work.**
- Every lane is standalone and independently runnable.
- The main agent owns completion. Delegation is role-based and must not create duplicate competing implementations.
- Use **XHigh for hard architecture, root-cause analysis, visual/spatial judgment, and final adversarial review when available**. Do not automatically downgrade to High just to save quota; higher effort may reduce retries and total consumption.
- A worker may be downgraded only when its task is bounded/repetitive and the lower tier is sufficient.
- Research/log/indexing workers must not make final architectural decisions.
- Final completion claims require evidence from real tests, not successful tool-call receipts alone.

## Handoffs
1. [Blender WebGPT Bridge / MCP-Plus](01_BLENDER_WEBGPT_BRIDGE_MCP_PLUS.md)
2. [OpenCode CLI ↔ WebGPT Plugin](02_OPENCODE_WEBGPT_PLUGIN.md)
3. [Unity Agent Plugin](03_UNITY_AGENT_PLUGIN.md)
4. [Game Development Core Integration](04_GAME_DEVELOPMENT_CORE.md)
5. [CANONFLOW / PINFRAME / Visual Handoff](05_CANONFLOW_PINFRAME_VISUAL_HANDOFF.md)
6. [LASTLINE: ECHOES / LIN ASTER / 3D](06_LASTLINE_ECHOES_3D_VISUAL.md)
7. [NOIN / 70세 노인 용사](07_NOIN_STORY_PRODUCTION.md)
8. [Suno / Lyria Music Pipeline](08_AI_MUSIC_PIPELINE.md)
9. [AI Music Video Production](09_AI_MUSIC_VIDEO.md)
10. [Life-Agent OS / APK](10_LIFE_AGENT_OS.md)
11. [DeepSeek V4.1 Flash Design Beta](11_DEEPSEEK_DESIGN_BETA.md)
12. [Atlas.design Absorption](12_ATLAS_DESIGN_ABSORPTION.md)
13. [Kimaki / Oracle / Three.js / WebGPT Toolchain](13_LOCAL_AI_TOOLCHAIN.md)
14. [SoL-Pi / sprite-gen / New Game Tech Intake](14_GAME_TECH_INTAKE.md)
15. [Storage Regression / Offloader / Hourly Repair](15_STORAGE_OFFLOADER_REPAIR.md)
16. [Support Programs / Funding / Positioning](16_SUPPORT_FUNDING_POSITIONING.md)
17. [Email Triage / Interest Filter](17_EMAIL_TRIAGE.md)
18. [AI / Game / Music / Video Tech Scouting](18_TECH_SCOUTING.md)

## Priority
Start first: **01, 04, 06, 10**. Then: **02, 03, 05, 09, 15**. The rest can run in parallel where dependencies permit.
