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

## Handoffs — model routing visible before opening

| # | Work handoff | MAIN | Key subagents |
|---|---|---|---|
| 01 | [Blender WebGPT Bridge / MCP-Plus](01_BLENDER_WEBGPT_BRIDGE_MCP_PLUS.md) | **Astra XHigh** | Sol High implementation · Astra XHigh visual/final QA · Terra High regression · Luna Medium evidence |
| 02 | [OpenCode CLI ↔ WebGPT Plugin](02_OPENCODE_WEBGPT_PLUGIN.md) | **Sol XHigh** | Sol High implementation · Astra XHigh security/final audit · Terra High fault tests · Luna Medium logs |
| 03 | [Unity Agent Plugin](03_UNITY_AGENT_PLUGIN.md) | **Sol XHigh** | Sol High implementation · Astra High→XHigh structural review · Terra High journey tests · Luna Medium inventory |
| 04 | [Game Development Core Integration](04_GAME_DEVELOPMENT_CORE.md) | **Astra XHigh** | Astra XHigh architecture challenger · Sol High implementation · Terra High vertical-slice tests · Luna Medium scouting |
| 05 | [CANONFLOW / PINFRAME / Visual Handoff](05_CANONFLOW_PINFRAME_VISUAL_HANDOFF.md) | **Astra XHigh** | Astra High→XHigh visual UX QA · Sol High implementation · Terra High data-integrity tests · Luna Medium import/inventory |
| 06 | [LASTLINE: ECHOES / LIN ASTER / 3D](06_LASTLINE_ECHOES_3D_VISUAL.md) | **Astra XHigh** | Astra XHigh visual/canon QA · Sol High 3D pipeline · Terra High canon regression · Luna Medium reference inventory |
| 07 | [NOIN / 70세 노인 용사](07_NOIN_STORY_PRODUCTION.md) | **Sol XHigh** | Sol High continuity editor · Astra High story challenger · Terra Medium quantitative checks · Luna Medium inventory |
| 08 | [Suno / Lyria Music Pipeline](08_AI_MUSIC_PIPELINE.md) | **Sol High** | Sol High integration · Astra High music-quality review · Terra Medium reproducibility · Luna Medium provider research |
| 09 | [AI Music Video Production](09_AI_MUSIC_VIDEO.md) | **Astra XHigh** | Astra XHigh temporal/continuity QA · Sol High pipeline · Terra High clip/failure tests · Luna Medium provider research |
| 10 | [Life-Agent OS / APK](10_LIFE_AGENT_OS.md) | **Astra XHigh** | Astra XHigh privacy/safety audit · Sol High/XHigh hard implementation · Terra High device tests · Luna Medium evidence |
| 11 | [DeepSeek V4.1 Flash Design Beta](11_DEEPSEEK_DESIGN_BETA.md) | **Astra High→XHigh** | Astra XHigh visual judge · Sol High harness/integration · Terra Medium scoring · Luna Medium evidence research |
| 12 | [Atlas.design Absorption](12_ATLAS_DESIGN_ABSORPTION.md) | **Astra High** | Astra High→XHigh final UX judge · Sol High implementation · Terra Medium comparison tests · Luna Medium research |
| 13 | [Kimaki / Oracle / Three.js / WebGPT Toolchain](13_LOCAL_AI_TOOLCHAIN.md) | **Sol XHigh** | Sol High integration · Astra High final audit · Terra High compatibility tests · Luna Medium dependency inventory |
| 14 | [SoL-Pi / sprite-gen / New Game Tech Intake](14_GAME_TECH_INTAKE.md) | **Sol High** | Sol High integration feasibility · Astra High architecture escalation only · Terra Medium smoke tests · Luna Medium scouting |
| 15 | [Storage Regression / Offloader / Hourly Repair](15_STORAGE_OFFLOADER_REPAIR.md) | **Sol XHigh** | Sol High debugging · Astra XHigh data-safety audit · Terra High fault injection · Luna Medium storage/log collection |
| 16 | [Support Programs / Funding / Positioning](16_SUPPORT_FUNDING_POSITIONING.md) | **Sol High** | Astra High positioning judge · Terra Medium eligibility verification · Luna Medium official-source research |
| 17 | [Email Triage / Interest Filter](17_EMAIL_TRIAGE.md) | **Sol Medium** | Luna Medium first-pass · Terra Medium importance verification · Astra High only for high-stakes ambiguity |
| 18 | [AI / Game / Music / Video Tech Scouting](18_TECH_SCOUTING.md) | **Sol Medium** | Luna Medium scouting · Terra Medium evidence verification · Astra High→XHigh major adoption decisions · Sol High integration planning |

## Priority
Start first: **01, 04, 06, 10**. Then: **02, 03, 05, 09, 15**. The rest can run in parallel where dependencies permit.

## Reading rule
The model shown in the **MAIN** column is the model/reasoning setting to select when opening that Work. Subagent routing is already embedded inside each one-shot handoff file, so the Work should preserve those assignments unless a model is genuinely unavailable.