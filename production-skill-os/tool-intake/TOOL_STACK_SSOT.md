# TOOL STACK SSOT — Production Skill OS to LIN ASTER 3D

**Registry ID:** `GLOBAL_TOOL_CAPABILITY_REGISTRY_20260914`
**Status:** `CANDIDATE_FAIL_CLOSED`
**Generated:** `2026-09-14`
**Candidate branch:** `candidate/tool-capability-lin3d-gate-v2-20260914`
**Base head:** `7f9c5701a77d341bd7ca680b06242980600000dd`
**Final lock authority:** `USER_ONLY`

## Bottom line

The recovered portfolio contains **40 capability records**.
There are **0 `VERIFIED_FOR_LIN_3D`** records.
Only two internal, non-3D-mutating capabilities are absorbed generically: registry validation
and fail-closed selection. Every external LIN-relevant capability remains validation-only,
blocked, reviewed, watch, or superseded until its own evidence gate is satisfied.

## Current LIN authority

```text
repo=Kyuha927/lastline-echoes
branch=lin-aster-tripo-r01-20260913
head=e1b02b1773366677a543d764bd68638e13da1a27
ssot_blob=612fd6347f7d203f9b6d8a3737a72bbaf7a6f0fe
live_state_blob=f44c283bd5c02a1a8e8b3adf7785c867d78b0c2f
policy=LIN_ASTER_3D_PRODUCTION_CONTROL_V1_2
```

The current project route is R04 H3.1 component generation and controlled reconstruction.
P2 full-body hero-base authority is superseded. The candidate registry must be reconciled
again whenever the authority branch advances.

## Status inventory

| Status | Count | Capability IDs |
|---|---|---|
| REVIEWED | 5 | cap.tripo.r03.h31_full_body_detail_donor, cap.work03.unity_agent_plugin_scene_compile_play_capture, cap.work16.funding_official_source_table, cap.switchyard.multi_agent_routing, cap.microsoft.ai_engineering_coach |
| TEST_REQUIRED | 5 | cap.tripo.h31.multiview_input_contract, cap.blender.headless_reviewed_bpy, cap.oracle.browser_provider_routing, cap.threejs_game_skills.asset_recovery_qa, cap.unity_agent_plugin.official_editor_agent |
| ISOLATED_PASS | 12 | cap.blender_bridge.offline_packaged_core, cap.work04.three_js_relay_grid_vertical_slice, cap.work07.noin_continuity_quantitative_checks, cap.work08.ai_music_candidate_recovery, cap.work09.ai_music_video_offline_postprocess, cap.work10.life_agent_apk_static_build_evidence, cap.work12.atlas_approval_state_absorption, cap.work13.local_three_js_toolchain, cap.work14.sol_pi_sprite_gen_intake, cap.work15.storage_resume_repair, cap.work17.read_only_email_triage, cap.work18.technology_scouting_decision_log |
| ISOLATED_FAIL | 3 | cap.work05.canonflow_pinframe_roundtrip, cap.work06.lin_r19_visual_candidate, cap.work11.deepseek_design_beta |
| WATCH | 1 | cap.pencil_creator.unity_blender_knowledge |
| ABSORBED_GENERIC | 2 | cap.production_skill_os.registry_validation, cap.production_skill_os.fail_closed_selection |
| LIN_3D_TEST_REQUIRED | 8 | cap.tripo.h31.head_component_ultra, cap.tripo.h31.hair_component_ultra, cap.tripo.h31.body_outfit_component_ultra, cap.tripo.h31.coat_component_ultra, cap.blender_bridge.transactional_edit_render_reopen_rollback, cap.astra.computer_use.visual_blender_assembly, cap.lin.controlled_manual_retopology, cap.lin.mobile_hero_real_device_validation |
| SUPERSEDED | 1 | cap.tripo.p2.full_body_primary_hero_base |
| BLOCKED | 3 | cap.blender_bridge.current_tunnel_transport, cap.work01.blender_bridge_mcp_plus, cap.work02.opencode_to_webgpt_plugin |

## Selection invariant

```text
requested operation
→ identify capability ID
→ request exact version/commit and scope
→ validate registry and current LIN authority
→ ALLOW only when that scope's evidence contract passes
→ otherwise DENY with an exact blocker
```

`LIN_3D_FINAL` is never inferred from `ISOLATED_PASS`, documentation, repository CI, provider
success, or a tool receipt. It requires `VERIFIED_FOR_LIN_3D` and L8 same-path evidence.
Validation must be isolated and cannot mutate production or canon.

## Ownership boundaries

Tripo supplies candidate geometry; Astra performs supervised visual/spatial judgment; Sol Pro
performs analysis/specification/delta QA; Bridge or reviewed deterministic tools provide exact
state and receipts; human corrections are recorded; the user alone approves final lock.
