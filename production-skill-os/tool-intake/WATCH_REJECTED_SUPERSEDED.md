# Watch / Rejected / Superseded / Blocked

The following records have no authorized production or validation scope unless their status and evidence
are deliberately changed through a reviewed registry update.

| Capability ID | Status | Key failure/blocker | Superseded by | Next gate |
|---|---|---|---|---|
| cap.tripo.p2.full_body_primary_hero_base | SUPERSEDED | HERO_IDENTITY_AND_COMPONENT_FIDELITY_INSUFFICIENT; DESIGN_ARCHITECTURE_MISMATCH | ['cap.tripo.h31.head_component_ultra', 'cap.tripo.h31.hair_component_ultra', 'cap.tripo.h31.body_outfit_component_ultra', 'cap.tripo.h31.coat_component_ultra'] | DO_NOT_SELECT_FOR_LIN_3D_FINAL |
| cap.blender_bridge.current_tunnel_transport | BLOCKED | GATEWAY_OR_SSE_404; LIVE_BUILD_IDENTITY_UNREADABLE | - | READ_ONLY_BRIDGE_HEALTH_MUST_RETURN_EXACT_BUILD_AND_WORKSPACE_IDENTITY |
| cap.work01.blender_bridge_mcp_plus | BLOCKED | Missing durable live endpoint/auth evidence; current transport probe is also 404. | - | Restore exact authorized endpoint and run live end-to-end. |
| cap.work02.opencode_to_webgpt_plugin | BLOCKED | Attachment URL found but ZIP bytes, SHA, tests, and actual integration were not verified. | - | Recover exact artifact and test in an isolated checkout. |
| cap.work05.canonflow_pinframe_roundtrip | ISOLATED_FAIL | Long-input reopen/backup, score persistence, note loss, and overlap defects remained. | - | Repair roundtrip and mobile defects before adoption. |
| cap.work06.lin_r19_visual_candidate | ISOLATED_FAIL | Saved candidate and nine renders existed; face/hair similarity was insufficient. | - | Do not promote; use as failure evidence only. |
| cap.work11.deepseek_design_beta | ISOLATED_FAIL | 22 calls/four HTML outputs but stale state/blank result and no blind visual review. | - | Build discriminating pairs and complete blind review. |
| cap.pencil_creator.unity_blender_knowledge | WATCH | LICENSE_UNRESOLVED; DUPLICATE_SYSTEM_RISK; NO_CURRENT_REPRESENTATIVE_TEST | - | Run representative LIN-adjacent tasks and inspect license/dependency footprint before absorbing any rule. |
