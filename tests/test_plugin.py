import importlib.util
import json
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PluginConfigTest(unittest.TestCase):
    def test_mcp_points_at_the_remote_server(self):
        raw = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(list(raw["mcpServers"]), ["pokitnote"])
        server = raw["mcpServers"]["pokitnote"]
        self.assertEqual(server["type"], "http")
        self.assertNotIn("command", server)
        self.assertNotIn("args", server)
        self.assertEqual(server["url"], "${POKITNOTE_API_BASE}")
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

    def test_marketplace_and_manifest(self):
        market = json.loads((ROOT / ".cursor-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(market["plugins"][0]["name"], "pokit-note")
        plugin = json.loads((ROOT / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["mcpServers"], "./mcp.json")
        variables = plugin["variables"]
        self.assertEqual(variables["type"], "object")
        self.assertNotIn("POKITNOTE_API_BASE", variables.get("required", []))
        address = variables["properties"]["POKITNOTE_API_BASE"]
        self.assertEqual(address["title"], "Pokit Note address")
        self.assertEqual(address["type"], "string")
        self.assertEqual(address["default"], "https://pokitnote.com/mcp")
        self.assertNotIn("mcp/", address["default"])
        self.assertNotIn("mcp/", address["description"])
        self.assertIn("no trailing slash", address["description"])
        self.assertNotIn("pnt_", json.dumps(plugin))
        self.assertEqual(plugin["logo"], "assets/logo.png")
        logo = (ROOT / plugin["logo"]).read_bytes()
        self.assertTrue(logo.startswith(b"\x89PNG\r\n\x1a\n"))
        width, height = struct.unpack(">II", logo[16:24])
        self.assertEqual((width, height), (256, 256))

    def test_coffee_and_tea_follows_beverages(self):
        for relative in ("skills/pokit-note/SKILL.md", "README.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("Beverages, Coffee & Tea, Dairy & Eggs", text)
            self.assertIn(
                "Coffee beans, ground coffee, K-cups, and tea go in Coffee & Tea, not Beverages.",
                text,
            )

    def test_pet_food_follows_frozen_foods(self):
        for relative in ("skills/pokit-note/SKILL.md", "README.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("Frozen Foods, Pet Food, and Other", text)
            self.assertIn(
                "Dog and cat food, treats, and litter go in Pet Food.",
                text,
            )

    def test_address_override_cannot_ship_a_non_production_default(self):
        spec = importlib.util.spec_from_file_location(
            "validate_plugin", ROOT / "scripts" / "validate_plugin.py"
        )
        if spec is None or spec.loader is None:
            self.fail("could not load scripts/validate_plugin.py")
        validate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validate)

        plugin = json.loads((ROOT / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertIsNone(
            validate.resolved_mcp_url_problem("${POKITNOTE_API_BASE}", plugin["variables"])
        )
        self.assertIsNone(validate.resolved_mcp_url_problem("https://pokitnote.com/mcp", None))
        self.assertIsNotNone(validate.resolved_mcp_url_problem("https://pokitnote.com/mcp/", None))
        slashed_default = {
            "type": "object",
            "properties": {
                "POKITNOTE_API_BASE": {
                    "type": "string",
                    "default": "https://pokitnote.com/mcp/",
                }
            },
        }
        self.assertIsNotNone(
            validate.resolved_mcp_url_problem("${POKITNOTE_API_BASE}", slashed_default)
        )
        for url in ("https://stage.pokitnote.com/mcp", "https://api.pokitnote.com/mcp"):
            self.assertIsNotNone(validate.resolved_mcp_url_problem(url, None), url)
            staged = {
                "type": "object",
                "properties": {"POKITNOTE_API_BASE": {"type": "string", "default": url}},
            }
            self.assertIsNotNone(
                validate.resolved_mcp_url_problem("${POKITNOTE_API_BASE}", staged),
                url,
            )
        required = {
            "type": "object",
            "required": ["POKITNOTE_API_BASE"],
            "properties": {
                "POKITNOTE_API_BASE": {
                    "type": "string",
                    "default": "https://pokitnote.com/mcp",
                }
            },
        }
        self.assertIsNotNone(validate.resolved_mcp_url_problem("${POKITNOTE_API_BASE}", required))
        missing_default = {
            "type": "object",
            "properties": {"POKITNOTE_API_BASE": {"type": "string"}},
        }
        self.assertIsNotNone(
            validate.resolved_mcp_url_problem("${POKITNOTE_API_BASE}", missing_default)
        )
        skill = (ROOT / "skills/pokit-note/SKILL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for text in (skill, readme):
            self.assertIn("https://pokitnote.com/mcp", text)
            self.assertNotIn("https://pokitnote.com/mcp/", text)
            self.assertIn("no trailing slash", text)
            self.assertIn("Leave Pokit Note address unset", text)
            self.assertNotIn("no address setting", text)

    def test_shared_link_goes_in_item_note(self):
        text = (ROOT / "skills/pokit-note-connected-assistant/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("always put the page link in that item's note", text)


if __name__ == "__main__":
    unittest.main()
