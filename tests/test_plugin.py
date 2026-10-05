import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = "https://example.invalid"


class PluginConfigTest(unittest.TestCase):
    def test_mcp_points_at_the_remote_server(self):
        raw = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(list(raw["mcpServers"]), ["pokitnote"])
        server = raw["mcpServers"]["pokitnote"]
        self.assertEqual(server["type"], "http")
        self.assertNotIn("command", server)
        self.assertNotIn("args", server)
        self.assertEqual(server["url"].replace("${POKITNOTE_API_BASE}", EXAMPLE), f"{EXAMPLE}/mcp/")
        self.assertEqual(server["auth"]["CLIENT_ID"], "grok-bot")
        self.assertEqual(server["auth"]["scopes"], ["notes"])
        self.assertNotIn("CLIENT_SECRET", server["auth"])
        text = json.dumps(raw)
        self.assertNotIn("python", text.lower())
        self.assertNotIn("pnt_", text)
        self.assertNotIn("pnoa_", text)
        self.assertNotIn("pnor_", text)

    def test_the_local_server_is_not_shipped(self):
        self.assertFalse((ROOT / "server").exists())

    def test_marketplace_skills_and_address_stay(self):
        market = json.loads((ROOT / ".cursor-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(market["plugins"][0]["name"], "pokit-note")
        plugin = json.loads((ROOT / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(
            plugin["variables"]["properties"]["POKITNOTE_API_BASE"]["default"],
            "https://stage.pokitnote.com",
        )
        self.assertNotIn("pnt_", json.dumps(plugin))
        skill = (ROOT / "skills" / "pokit-note" / "SKILL.md").read_text(encoding="utf-8")
        command = (ROOT / "commands" / "sign-in.md").read_text(encoding="utf-8")
        for text in (skill, command):
            self.assertIn("Authenticate", text)
            self.assertNotIn("python", text.lower())
            self.assertNotIn("pnt_", text)
        self.assertIn("notes", skill)
        self.assertIn("Grocery Shopping", skill)
        self.assertIn("recipe", skill)


if __name__ == "__main__":
    unittest.main()
