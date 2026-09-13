# Portfolio Reconciliation — 2026-09-14

## Recovered scope

This reconciliation combines the corrected 18-lane Work audit, later tool/repository reviews,
the existing Production Skill OS candidate, the Blender Bridge candidate, official Tripo
production/model documentation, and the current LIN ASTER R04 authority. The corrected Work
audit boundary remains: broad product/integration completion was not established for 18/18;
limited sub-scope evidence is not treated as global adoption.

## Complete capability inventory

| Capability ID | Tool/System | Capability | Status | Evidence | Pinned version/commit | LIN relevance | Next gate |
|---|---|---|---|---|---|---|---|
| cap.production_skill_os.registry_validation | Production Skill OS | Capability registry structural and evidence validation | ABSORBED_GENERIC | L7 | 1.0.0-candidate.20260914 | INDIRECT | CI_ON_CANDIDATE_BRANCH_THEN_USER_REVIEW |
| cap.production_skill_os.fail_closed_selection | Production Skill OS | Fail-closed capability authorization by scope and exact version | ABSORBED_GENERIC | L7 | 1.0.0-candidate.20260914 | DIRECT_CONTROL_PLANE | CI_ON_CANDIDATE_BRANCH_THEN_USER_REVIEW |
| cap.tripo.h31.head_component_ultra | Tripo H3.1 | H3.1 Ultra head/face/neck component generation | LIN_3D_TEST_REQUIRED | L1 | v3.1-20260211 | DIRECT | RUN_R04_HEAD_AFTER_LINEAGE_REFERENCE_PREP |
| cap.tripo.h31.hair_component_ultra | Tripo H3.1 | H3.1 Ultra hair/braid/silhouette component generation | LIN_3D_TEST_REQUIRED | L1 | v3.1-20260211 | DIRECT | RUN_R04_HAIR_AFTER_LINEAGE_REFERENCE_PREP |
| cap.tripo.h31.body_outfit_component_ultra | Tripo H3.1 | H3.1 Ultra body/outfit component generation | LIN_3D_TEST_REQUIRED | L1 | v3.1-20260211 | DIRECT | RUN_R04_BODY_AFTER_LINEAGE_REFERENCE_PREP |
| cap.tripo.h31.coat_component_ultra | Tripo H3.1 | H3.1 Ultra coat/major-garment donor generation | LIN_3D_TEST_REQUIRED | L1 | v3.1-20260211 | DIRECT | RUN_R04_COAT_IF_COHERENT_REFERENCE_EXISTS |
| cap.tripo.h31.multiview_input_contract | Tripo H3.1 | Four-direction multiview ordering and consistency contract | TEST_REQUIRED | L1 | v3.1-20260211 | DIRECT | PART_SPECIFIC_REFERENCE_CONSISTENCY_CHECK |
| cap.tripo.p2.full_body_primary_hero_base | Tripo Smart Mesh P2.0 | Full-body Native Quad as LIN hero production base | SUPERSEDED | L6 | LIN_R03_P20_4VIEW_QUAD_BASE_A | DIRECT | DO_NOT_SELECT_FOR_LIN_3D_FINAL |
| cap.tripo.r03.h31_full_body_detail_donor | Tripo H3.1 | R03 full-body high-detail donor | REVIEWED | L6 | LIN_R03_H31_4VIEW_DETAIL_B | DIRECT | COMPARE_AS_DONOR_AFTER_R04_COMPONENT_SET_EXISTS |
| cap.blender_bridge.offline_packaged_core | Blender Pro Bridge 0.5.0a2 | Packaged deterministic bridge core and offline regression surface | ISOLATED_PASS | L4 | e8095fea25cb2f8a1eb56dcb2b7be442d5ffa854 / 0.5.0a2 | DIRECT | RESTORE_CURRENT_BRIDGE_CONNECTIVITY_AND_RUN_SAME_SCENE_LIN_E2E |
| cap.blender_bridge.current_tunnel_transport | Blender Pro Bridge Local | Current WebGPT-to-local bridge transport | BLOCKED | L5 | EXPECTED_0.5.0a2_BUT_LIVE_IDENTITY_UNREADABLE | DIRECT | READ_ONLY_BRIDGE_HEALTH_MUST_RETURN_EXACT_BUILD_AND_WORKSPACE_IDENTITY |
| cap.blender_bridge.transactional_edit_render_reopen_rollback | Blender Pro Bridge 0.5.0a2 | Transactional edit, rendered pixels, checkpoint, fresh reopen, rollback | LIN_3D_TEST_REQUIRED | L4 | e8095fea25cb2f8a1eb56dcb2b7be442d5ffa854 / 0.5.0a2 | DIRECT | SAME_SCENE_LIN_E2E_AFTER_SELECTED_R04_PARTS |
| cap.astra.computer_use.visual_blender_assembly | GPT-6 Astra Computer Use | Supervised visual/spatial Blender assembly and high-consequence judgment | LIN_3D_TEST_REQUIRED | L1 | CURRENT_ACCOUNT_ROUTE_UNKNOWN_UNTIL_RUN | DIRECT | RUN_AFTER_SELECTED_R04_COMPONENT_SET_AND_PRIVATE_IMPORT_PREFLIGHT |
| cap.blender.headless_reviewed_bpy | Blender / reviewed bpy | Bounded deterministic inspection, conversion, batch render, bake, and export | TEST_REQUIRED | L2 | BLENDER_4.5.4_LTS_EXPECTED; EXACT_SCRIPT_HASH_REQUIRED_PER_RUN | DIRECT | DECLARE_EXACT_SCRIPT_AND_RUN_DISPOSABLE_FIXTURE_SMOKE |
| cap.lin.controlled_manual_retopology | Blender manual/reviewed retopology | Controlled/manual retopology and reconstruction for final animated topology | LIN_3D_TEST_REQUIRED | L2 | R04_POLICY_AT_e1b02b1773366677a543d764bd68638e13da1a27 | DIRECT | OBSERVE_SELECTED_R04_PARTS_THEN_DEFINE_PART_SPECIFIC_RETOPO_PLAN |
| cap.lin.mobile_hero_real_device_validation | LIN Mobile Hero validation | Real-device character microbench plus sustained traversal/combat thermal evidence | LIN_3D_TEST_REQUIRED | L2 | LIN_ASTER_3D_PRODUCTION_CONTROL_V1_2 | DIRECT | WAIT_FOR_ART_MASTER_CANDIDATE |
| cap.work01.blender_bridge_mcp_plus | Recovered Work lane 01 | Blender Bridge MCP Plus | BLOCKED | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | DIRECT | Restore exact authorized endpoint and run live end-to-end. |
| cap.work02.opencode_to_webgpt_plugin | Recovered Work lane 02 | OpenCode to WebGPT plugin | BLOCKED | L2 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | INDIRECT | Recover exact artifact and test in an isolated checkout. |
| cap.work03.unity_agent_plugin_scene_compile_play_capture | Recovered Work lane 03 | Unity Agent plugin scene/compile/play/capture | REVIEWED | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | INDIRECT | Reproduce with current official Unity Agent version and verify runtime input state. |
| cap.work04.three_js_relay_grid_vertical_slice | Recovered Work lane 04 | Three.js Relay Grid vertical slice | ISOLATED_PASS | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Keep generic; do not infer LIN or engine-wide readiness. |
| cap.work05.canonflow_pinframe_roundtrip | Recovered Work lane 05 | CANONFLOW/PINFRAME roundtrip | ISOLATED_FAIL | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Repair roundtrip and mobile defects before adoption. |
| cap.work06.lin_r19_visual_candidate | Recovered Work lane 06 | LIN R19 visual candidate | ISOLATED_FAIL | L6 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | DIRECT | Do not promote; use as failure evidence only. |
| cap.work07.noin_continuity_quantitative_checks | Recovered Work lane 07 | NOIN continuity quantitative checks | ISOLATED_PASS | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Retain as story-domain isolated evidence only. |
| cap.work08.ai_music_candidate_recovery | Recovered Work lane 08 | AI music candidate recovery | ISOLATED_PASS | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Run audio review and rights verification before production use. |
| cap.work09.ai_music_video_offline_postprocess | Recovered Work lane 09 | AI music video offline postprocess | ISOLATED_PASS | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Test on final licensed source and full-length render. |
| cap.work10.life_agent_apk_static_build_evidence | Recovered Work lane 10 | Life-Agent APK static/build evidence | ISOLATED_PASS | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Run device install/startup and representative permission flows. |
| cap.work11.deepseek_design_beta | Recovered Work lane 11 | DeepSeek design beta | ISOLATED_FAIL | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Build discriminating pairs and complete blind review. |
| cap.work12.atlas_approval_state_absorption | Recovered Work lane 12 | Atlas approval-state absorption | ISOLATED_PASS | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Keep only the generic state-machine pattern. |
| cap.work13.local_three_js_toolchain | Recovered Work lane 13 | Local Three.js toolchain | ISOLATED_PASS | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Retain generic bounded adapter evidence. |
| cap.work14.sol_pi_sprite_gen_intake | Recovered Work lane 14 | SoL-Pi / sprite-gen intake | ISOLATED_PASS | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Keep in experiment lane. |
| cap.work15.storage_resume_repair | Recovered Work lane 15 | Storage resume repair | ISOLATED_PASS | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Run byte-identical remote restore and measured disk behavior. |
| cap.work16.funding_official_source_table | Recovered Work lane 16 | Funding official-source table | REVIEWED | L2 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Reverify current official program eligibility/deadlines. |
| cap.work17.read_only_email_triage | Recovered Work lane 17 | Read-only email triage | ISOLATED_PASS | L5 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | NONE | Keep read-only and separately authorize any mutation. |
| cap.work18.technology_scouting_decision_log | Recovered Work lane 18 | Technology scouting decision log | ISOLATED_PASS | L4 | UNKNOWN_LOCAL_ARTIFACT_IDENTITY_NOT_FULLY_RECOVERED | INDIRECT | Use only as intake; every ACT NOW item needs its own capability gate. |
| cap.switchyard.multi_agent_routing | NVIDIA NeMo Switchyard | Multi-agent routing/orchestration research candidate | REVIEWED | L1 | 9b6efb94cedadca4652e2e4c3e014abed2c44831 | INDIRECT | Compare bounded routing/observability capabilities against the existing Production Skill OS without replacing the control plane. |
| cap.microsoft.ai_engineering_coach | Microsoft AI Engineering Coach | Engineering-coach workflow patterns | REVIEWED | L1 | 18b1a3d16b586c171426c6a407cc5c2dc073556e | NONE | Extract useful review/learning patterns only after license and overlap analysis. |
| cap.pencil_creator.unity_blender_knowledge | psmon/pencil-creator | 2D/3D/Unity craft knowledge and failure heuristics | WATCH | L1 | 9984c47c92e4995b0715a515efb2883e80281c92 | INDIRECT | Run representative LIN-adjacent tasks and inspect license/dependency footprint before absorbing any rule. |
| cap.oracle.browser_provider_routing | steipete/oracle | Browser/provider review routing | TEST_REQUIRED | L1 | ad19526c9bb10c10223684c85200b3b135457db5 | INDIRECT | Test exact local WebGPT replacement workflow; do not infer compatibility from repository presence. |
| cap.threejs_game_skills.asset_recovery_qa | threejs-game-skills | Resumable asset generation and evidence-based QA patterns | TEST_REQUIRED | L1 | e5f301d548bb18c530afbece78cd25082f4cda9c | INDIRECT | Test atomic Tripo checkpoint ideas against current R04 evidence without executing paid generation. |
| cap.unity_agent_plugin.official_editor_agent | Unity Agent Plugin | Official Unity editor agent integration | TEST_REQUIRED | L1 | c7055702b44e58402ee481ff408aee407bcf9483 / 0.1.6-beta manifest | INDIRECT | Run current official plugin in an isolated Unity project and verify compile, PlayMode, runtime input, and capture. |

## Reconciliation rules applied

- duplicate or overlapping orchestration was not adopted;
- official documentation and repository health are review evidence, not same-path proof;
- isolated PASS remains bounded to its exact environment and execution path;
- blocked, failed, watch, and superseded entries have no authorized scope;
- R04 H3.1 parts may enter only isolated LIN validation until real outputs and same-path evidence exist;
- existing failure knowledge and the new capability gate remain separate layers;
- no production/canon mutation occurred during this reconciliation.
