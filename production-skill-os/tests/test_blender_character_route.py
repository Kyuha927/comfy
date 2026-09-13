import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "blender-character-tripo-astra" / "SKILL.md"
CONSUMER = ROOT / "docs" / "CONSUMER_INTEGRATION.md"
REGISTRY = ROOT / "tool-intake" / "TOOL_CAPABILITY_REGISTRY.json"
CONTRACT = ROOT / "tool-intake" / "SELECTION_CONTRACT.json"
GUARD = ROOT / "router" / "capability_guard.py"
ADAPTER = ROOT / "adapters" / "authorize_capability.py"


class BlenderCharacterRoutePolicyTests(unittest.TestCase):
    def test_executable_capability_gate_is_bound(self):
        skill = SKILL.read_text(encoding="utf-8")
        consumer = CONSUMER.read_text(encoding="utf-8")
        for token in (
            "authorize_capability.py",
            "LIN_3D_FINAL",
            "VERIFIED_FOR_LIN_3D",
            "LIN_3D_VALIDATION",
            "--isolated-workspace",
            "--no-production-mutation",
            "--no-canon-mutation",
        ):
            self.assertIn(token, skill + consumer)
        for path in (REGISTRY, CONTRACT, GUARD, ADAPTER):
            self.assertTrue(path.exists(), path)

    def test_latest_lin_authority_is_pinned_and_stale_sha_is_blocked(self):
        text = SKILL.read_text(encoding="utf-8") + CONSUMER.read_text(encoding="utf-8")
        self.assertIn("e1b02b1773366677a543d764bd68638e13da1a27", text)
        self.assertIn("612fd6347f7d203f9b6d8a3737a72bbaf7a6f0fe", text)
        self.assertIn("f44c283bd5c02a1a8e8b3adf7785c867d78b0c2f", text)
        self.assertIn("LIN_ASTER_3D_PRODUCTION_CONTROL_V1_2", text)

    def test_r04_h31_component_route_replaces_p2_full_body_hero_route(self):
        text = SKILL.read_text(encoding="utf-8") + CONSUMER.read_text(encoding="utf-8")
        self.assertIn("H3.1 ULTRA HEAD", text)
        self.assertIn("H3.1 ULTRA HAIR", text)
        self.assertIn("H3.1 ULTRA BODY / OUTFIT", text)
        self.assertIn("H3.1 ULTRA COAT", text)
        self.assertIn("P2_FULL_BODY_PRIMARY_HERO_BASE=false", text)
        self.assertIn("TRIPO_BASE_READY=false", text)
        self.assertIn("R03 B is a whole-character detail donor only", text)

    def test_reference_lineage_and_geometry_before_texture_are_preserved(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("LINEAGE-TRACKED NON-CANON DERIVED WORKING REFERENCES", text)
        self.assertIn("Do not fabricate a", text)
        self.assertIn("missing part view", text)
        self.assertIn("Do not texture, rig, or promote rejected geometry", text)
        self.assertIn("PRIVACY=PRIVATE", text)

    def test_control_roles_and_supervision_are_preserved(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("GPT-6 Astra XHigh / Computer Use", text)
        self.assertIn("GPT-5.6 Sol Pro", text)
        self.assertIn("Blender Bridge/MCP", text)
        self.assertIn("Reviewed bpy/headless Blender", text)
        self.assertIn("Recorded human correction", text)
        self.assertIn("Never run a one-shot unattended character build", text)
        self.assertIn("act\n→ inspect real geometry or pixels", text)

    def test_non_destructive_neck_expression_and_final_evidence(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("SEPARATE_ALIGNED", text)
        self.assertIn("expression-head mesh/state switching", text)
        self.assertIn("fresh-process save/reopen", text)
        self.assertIn("rollback/restore proof", text)
        self.assertIn("USER_ONLY", text)
        self.assertIn("A green CI run verifies the guard implementation, not 3D quality", text)


if __name__ == "__main__":
    unittest.main()
