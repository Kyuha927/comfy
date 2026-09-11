# LIFE AGENT OS — NEW CHAT HANDOFF

## 0. Start Here

Continue the **Life Agent OS** project from this document.

Do **not** turn each user example into a separate app or a permanent top-level product menu. Reservation, phone booking, insurance claims, bank transfer, SOOP/CHZZK live opening, RustDesk updates, benefit discovery, and PDF intake are **skills, adapters, recipes, or user customizations** inside one agent operating layer.

The product is not a collection of mini-apps. It is:

> A personal agent OS layer above Android, browsers, phone calls, notifications, documents, desktop companions, and AI executors. The user states a goal; the system chooses skills, execution methods, confirmation gates, verification evidence, and recovery paths.

## 1. Non-Negotiable Product Definition

```text
One Android app
One Agent Shell
One Context Engine
One Vault
One Policy Kernel
One Executor Router
One Persistent Task Graph
One Skill Registry
One Recipe Engine
One audit/verification model
```

Examples supplied by the user are typically one of these: Skill pack, Trigger → conditions → action recipe, service/app adapter, user preference or policy, context source, executor, or verification strategy. They are **not** reasons to make another APK.

### Correct mental model

```text
User goal
→ gather current context
→ identify capabilities
→ select and compose skills
→ choose cheapest safe executor
→ preview/confirm when policy requires
→ execute
→ verify real success evidence
→ recover or escalate
→ persist exact resume point
```

### Wrong mental model, never repeat

```text
"Insurance request" → make insurance app
"Streamer alert" → make streamer app
"RustDesk update" → make RustDesk app
"Benefit search" → add another fixed product tile
```

## 2. UX Direction

The desired usability is **Aside-level or better**, expanded beyond the browser to OS-level context.

The home screen must be a command surface and situational inbox, not an app drawer:

```text
What should I handle?
[natural-language / voice request]

Needs your action
In progress
Recently completed
Context-aware suggestions
```

Primary navigation should remain stable even as skills grow:

```text
Home | Tasks | Automations/Skills | My Data
```

Important UX rules:

- Show the next required action, not merely an internal status.
- Do not bury user confirmations.
- Do not expose model/provider complexity unless useful.
- Use large touch targets, strong hierarchy, plain Korean, and short flows.
- Prefer contextual suggestions over fixed feature grids.
- Most routine work should finish without opening the main app.
- Show exactly what will be submitted, changed, paid, or shared.
- Never mark complete from a button press alone. Require external evidence.

OS-level entry points should converge into the same Agent Shell: app launch, Android share sheet, selected-text action, notifications, Quick Settings tile, deep link/shortcut, voice/assistant role where available, and PC/Mac Companion events.

## 3. Core Architecture

### Agent Shell
One surface for text, voice, shared files, selected text, alerts, and resumable tasks.

### Context Engine
Combines only authorized context: current request/conversation, current app/screen when permitted, shared document or text, relevant notifications, current task graph, time and coarse location, connected-device state, explicit preferences and policies. Sensitive inferred attributes must not be silently converted into facts.

### Skill Registry
Every skill has a manifest similar to:

```text
id
capabilities
triggers
required inputs
permissions
risk
executors
preview
verification
fallbacks
configuration schema
```

### Policy Kernel

```text
AUTO
CONFIRM
BIOMETRIC
MANUAL_AUTH
BLOCK
```

Examples:

```text
Open selected livestream → AUTO
Analyze insurance documents → AUTO
Submit insurance claim → CONFIRM
Transfer money → BIOMETRIC + bank authentication
OTP/password/passkey step → MANUAL_AUTH
Bypass authentication → BLOCK
```

### Executor Router
Choose among official API, deterministic recipe/MODEL_FREE, Android Intent/app link, Autofill, local OCR/document processing, notification action, accessibility/mobile UI executor, PC/Mac Companion, phone/voice executor, Mobile Computer Use, Desktop Computer Use, and human action. AI model routing is subordinate to executor routing.

### Persistent Task Graph
Must persist goal, plan nodes, selected skills, selected executor and fallback, inputs/outputs, approval checkpoints, success evidence, failure code, retry count, and exact resume point.

## 4. Current Unified Build

```text
Filename: Life-Agent-OS-v2.1-benefits-pdf-alpha.apk
Package: com.lifeagent.unified
Version: 2.1.0-agent-os-alpha
Version code: 210
Minimum Android: Android 11 / API 30
SHA-256: 2eaffb1fd4fbaa937a7bc452f6c14e748e4c8a5230f1a13f47ffdbb85b30c32f
```

GitHub branch: `life-agent-os-v2.1-benefits-pdf-20260911`

Successful build run: `34586639020`

Artifact: `life-agent-os-v2.1-benefits-pdf-alpha` / artifact id `10193912684`.

Do not claim a new APK is complete until package, version, signature, alignment, and archive checks pass.

## 5. Implemented/Designed Skill Families

- Reservation skill: web/app/phone path selection, user constraints, phone executor, confirmation evidence, calendar handoff.
- Signup and secure autofill: shared Vault fields, Android Autofill executor, no password/OTP/PIN/CVV/recovery-code capture.
- Insurance claim skill pack: photo/document intake, on-device Korean OCR, document classification/cross-checking, Monimo handoff, Kakao follow-up, additional-document task creation, receipt-number verification.
- PDF insurance input v2.1: `application/pdf` intake, encrypted original PDF storage, `PdfRenderer`, on-device OCR, insurance Task Graph integration, fail-closed page/size limits.
- Transfer skill: draft, recipient/amount preview, biometric gate, bank/provider authentication, provider receipt verification.
- SOOP/CHZZK automation: exact trigger matching, model-free normal path, no lock-screen/authentication bypass.
- Software update monitor: RustDesk is a preset of a general update-monitor skill.
- Benefits discovery v2.1: explicit-interest tags, coarse/location-aware candidate discovery, continuous tracking only after opt-in, official-source application handoff, confirmation gates for identity/legal attestations.
- PC/Mac Companion: subordinate executor for desktop/browser/file actions, wake/display where supported, desktop Computer Use fallback, result verification returned to the same Task Graph.

## 6. Privacy and Safety Invariants

- One encrypted Vault, not feature-specific copies.
- Android Keystore protects local keys.
- Do not store passwords, OTPs, PINs, CVV/CVC, recovery codes, seed phrases, passkeys, or private keys.
- Models receive masked handles or purpose-limited values, not a full vault dump.
- Location monitoring is opt-in, revocable, visible, and minimized.
- Sensitive profile properties must not be guessed from casual dialogue and used as eligibility facts.
- Financial, legal attestation, identity verification, destructive, and irreversible actions require the applicable gate.
- No authentication bypass.
- No false completion. Store evidence.
- Fail closed when screen/app/provider behavior changes.

## 7. Current Known Boundaries

Still requiring real provider/device verification: real AI phone booking provider, current Monimo UI and real claim submission, real bank/open-banking execution, official subscription-model executor connection, Mobile/Desktop Computer Use provider integration, manufacturer-specific Android background behavior, SOOP/CHZZK real notification formats, PC wake/companion behavior on the user's devices, and benefits discovery against live official program sources/application portals.

A Samsung Life insurance-policy-loan FDS warning was observed in the prior chat. There is no established evidence that Life Agent caused it. Treat it as a separate security incident until proven otherwise. Do not automate around or bypass the warning.

## 8. First Actions in the New Chat

1. Confirm the user can download and install v2.1.
2. Test the Agent Shell and navigation before adding more skill logic.
3. Validate one low-risk end-to-end flow: share a harmless PDF → create a task → show plan/policy/executor → store/resume task.
4. Test benefits discovery with location disabled, approximate, and explicit opt-in foreground modes.
5. Fix defects in the same unified app.
6. Never spin out a separate APK for a single feature.

## 9. Paste This as the First Message in the New Chat

```text
Continue the Life Agent OS project from the attached handoff.

Treat every concrete example I give as a skill, adapter, recipe, context source, executor, policy, or customization inside one Agent OS unless I explicitly say otherwise. Do not create separate feature apps or keep adding a fixed feature-menu grid.

First verify the current unified APK and its actual install/runtime state. Preserve the OS-level architecture: Agent Shell, Context Engine, Skill Registry, Policy Kernel, Executor Router, Persistent Task Graph, Recipe Engine, shared Vault, verification evidence, and recovery. Improve UI/UX to Aside-level or better while extending beyond the browser into Android, notifications, calls, documents, location, and PC/Mac Companion.

Do not claim an external action works until it has been tested and verified with real evidence.
```
