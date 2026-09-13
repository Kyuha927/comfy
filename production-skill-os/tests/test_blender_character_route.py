import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "blender-character-tripo-astra" / "SKILL.md"
README = ROOT / "README.md"
CONSUMER = ROOT / "docs" / "CONSUMER_INTEGRATION.md"


class BlenderCharacterRoutePolicyTests(unittest.TestCase):
    def test_skill_exists_and_pins_primary_route(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("Tripo Smart Mesh P2.0", text)
        self.assertIn("GPT-6 Astra Computer Use is the primary interactive Blender path", text)
        self.assertIn("Blender Bridge/MCP is the secondary deterministic plane", text)
        self.assertIn("Do not ask GPT-6 Astra to create the character mesh from zero", text)

    def test_source_gated_part_strategy_and_hair_multiview_are_mandatory(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("DEDICATED_PART_REFERENCES", text)
        self.assertIn("FULL_BODY_MULTIVIEW_PART_AWARE", text)
        self.assertIn("Do not crop, mask, redraw, retouch, recolor, inpaint", text)
        self.assertIn("front, left, right, and back", text)
        self.assertIn("A single-view hair result is provisional", text)

    def test_evidence_and_fallback_guards_are_present(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("fresh-process save/reopen", text)
        self.assertIn("rollback proof", text)
        self.assertIn("No silent fallback is allowed", text)
        self.assertIn("user-review status, never automatic final approval", text)

    def test_docs_discover_and_bind_the_route(self):
        readme = README.read_text(encoding="utf-8")
        consumer = CONSUMER.read_text(encoding="utf-8")
        self.assertIn("blender-character-tripo-astra/SKILL.md", readme)
        self.assertIn("approved-parts->tripo-p2->astra-computer-use->bridge-verify", consumer)
        self.assertIn(
            "full-body-multiview->tripo-p2->part-aware-3d->astra-computer-use->bridge-verify",
            consumer,
        )
        self.assertIn("do not route zero-base character modeling to Astra", consumer)


if __name__ == "__main__":
    unittest.main()
