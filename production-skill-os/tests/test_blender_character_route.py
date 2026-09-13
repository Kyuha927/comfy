import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "blender-character-tripo-astra" / "SKILL.md"
README = ROOT / "README.md"
CONSUMER = ROOT / "docs" / "CONSUMER_INTEGRATION.md"
HANDOFF = (
    ROOT.parent
    / "releases"
    / "work-handoffs"
    / "2026-09-13-v5"
    / "BLENDER_CONTROL_PLANE_CONTINUE_NO_CANON_MERGE.md"
)


class BlenderCharacterRoutePolicyTests(unittest.TestCase):
    def test_skill_exists_and_pins_primary_route(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("Smart Mesh P2.0", text)
        self.assertIn("GPT-6 Astra Computer Use is the primary interactive Blender path", text)
        self.assertIn("Blender Bridge/MCP is the deterministic state-critical plane", text)
        self.assertIn("Do not ask GPT-6 Astra to create the character mesh from zero", text)
        self.assertIn("Do not encode this policy as a fixed percentage", text)

    def test_source_gated_part_strategy_and_hair_multiview_are_mandatory(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("DEDICATED_PART_REFERENCES", text)
        self.assertIn("FULL_BODY_MULTIVIEW_PART_AWARE", text)
        self.assertIn("Do not crop, mask, redraw, retouch, recolor, inpaint", text)
        self.assertIn("HEAD`, `HAIR`, and `BODY_CLOTHING", text)
        self.assertIn("front, left, right, and back", text)
        self.assertIn("A single-view hair result is provisional", text)

    def test_head_geometry_and_texture_commitment_are_guarded(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("approximately 2,000 to 5,000 polygons", text)
        self.assertIn("actual recessed orbital structure", text)
        self.assertIn("Eyeballs and pupils/irises must be independently addressable", text)
        self.assertIn("Treat texture generation as a post-geometry acceptance transition", text)
        self.assertIn("Preserve rejected Tripo job IDs", text)

    def test_supervised_loop_and_manual_lane_are_explicit(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("Do not run this as one unattended prompt", text)
        self.assertIn("character-specific preflight", text)
        self.assertIn("optional recorded human manual correction", text)
        self.assertIn("act\n-> inspect real geometry or pixels", text)

    def test_neck_and_expression_fallbacks_are_non_destructive(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("Do not force destructive neck welding as the default", text)
        self.assertIn("SEPARATE_ALIGNED", text)
        self.assertIn("explicit mesh/state switching", text)
        self.assertIn("do not force shape keys", text.lower())

    def test_rigging_helpers_are_declared_dependencies(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("Rigging and secondary-motion contract", text)
        self.assertIn("record its name, version, configuration, artifact hash or commit", text)
        self.assertIn("Do not claim the setup is reproducible without that dependency", text)

    def test_evidence_and_fallback_guards_are_present(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("fresh-process save/reopen", text)
        self.assertIn("rollback proof", text)
        self.assertIn("No silent fallback is allowed", text)
        self.assertIn("user-review status, never automatic final approval", text)
        self.assertIn("Merge-omission guards", text)

    def test_docs_discover_and_bind_the_complete_route(self):
        readme = README.read_text(encoding="utf-8")
        consumer = CONSUMER.read_text(encoding="utf-8")
        self.assertIn("blender-character-tripo-astra/SKILL.md", readme)
        self.assertIn(
            "approved-parts->tripo-p2->geometry-gate->astra-computer-use->bridge-verify",
            consumer,
        )
        self.assertIn(
            "full-body-multiview->tripo-p2->part-aware-3d->geometry-gate->astra-computer-use->bridge-verify",
            consumer,
        )
        self.assertIn("do not route zero-base character modeling to Astra", consumer)
        self.assertIn("treat texture generation as a post-geometry acceptance transition", consumer)
        self.assertIn("do not force destructive neck welding", consumer)
        self.assertIn("Merge-omission rejection", consumer)

    def test_safe_continuation_handoff_exists_and_cannot_claim_canon(self):
        text = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("HANDOFF_ID=BLENDER_CONTROL_PLANE_CONTINUE_NO_CANON_MERGE_V1", text)
        self.assertIn("TRIPO_FIRST=REQUIRED_WHEN_AUTHORIZED_AND_USABLE", text)
        self.assertIn("ASTRA_ZERO_BASE_CHARACTER_MODELING=FORBIDDEN", text)
        self.assertIn("VISUAL_INTERACTIVE_PRIMARY=GPT6_ASTRA_COMPUTER_USE", text)
        self.assertIn("DETERMINISTIC_STATE_CRITICAL_PRIMARY=BLENDER_BRIDGE_MCP_OR_REVIEWED_SCRIPT", text)
        self.assertIn("70948cc8e2f34d23d317d7fd798c6a2aa9de41d8", text)
        self.assertIn("AUTO_MERGE=false", text)
        self.assertIn("AUTO_CANON_PROMOTION=false", text)
        self.assertIn("READY_FOR_USER_REVIEW", text)


if __name__ == "__main__":
    unittest.main()
