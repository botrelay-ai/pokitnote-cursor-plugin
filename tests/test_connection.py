"""Plugin config for the remote Pokit Note MCP. These tests do not call a server."""

import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_BASE = "https://stage.pokitnote.com"


class AddressError(Exception):
    """The Pokit Note address cannot be used."""


def mcp_url(raw: str | None) -> str:
    """Build the Streamable HTTP MCP address from a Pokit Note server root."""
    value = (raw or "").strip()
    if not value or value.startswith("${"):
        value = DEFAULT_API_BASE
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise AddressError("The Pokit Note address needs to be a web address.")
    if parsed.username or parsed.password:
        raise AddressError("The Pokit Note address should not include a name or password.")
    if parsed.query or parsed.fragment:
        raise AddressError("The Pokit Note address should be only the server.")
    return value.rstrip("/") + "/mcp/"


class EndpointTests(unittest.TestCase):
    def test_empty_setting_uses_staging(self):
        self.assertEqual(mcp_url(""), f"{DEFAULT_API_BASE}/mcp/")
        self.assertEqual(mcp_url("${POKITNOTE_API_BASE}"), f"{DEFAULT_API_BASE}/mcp/")

    def test_custom_address_is_the_mcp_path(self):
        self.assertEqual(mcp_url("https://example.invalid"), "https://example.invalid/mcp/")
        self.assertEqual(mcp_url("https://example.invalid/"), "https://example.invalid/mcp/")

    def test_address_must_be_a_web_address(self):
        with self.assertRaises(AddressError):
            mcp_url("file:///tmp/pokitnote")
        with self.assertRaises(AddressError):
            mcp_url("https://user:secret@example.invalid")
        with self.assertRaises(AddressError):
            mcp_url("https://example.invalid/mcp?token=secret")


class PluginConfigTests(unittest.TestCase):
    def test_mcp_is_remote_http(self):
        mcp = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))
        server = mcp["mcpServers"]["pokit-note"]
        self.assertEqual(server["type"], "http")
        self.assertEqual(server["url"], "${POKITNOTE_API_BASE}/mcp/")
        self.assertEqual(server["auth"], {"CLIENT_ID": "grok-bot"})
        self.assertNotIn("command", server)
        self.assertNotIn("args", server)
        self.assertNotIn("env", server)
        self.assertNotIn("headers", server)
        blob = json.dumps(server)
        self.assertNotIn("CLIENT_SECRET", blob)
        self.assertNotIn("python", blob.lower())

    def test_template_resolves_without_calling_the_network(self):
        mcp = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))
        template = mcp["mcpServers"]["pokit-note"]["url"]
        resolved = template.replace("${POKITNOTE_API_BASE}", "https://example.invalid")
        self.assertEqual(resolved, mcp_url("https://example.invalid"))
        self.assertEqual(resolved, "https://example.invalid/mcp/")
        self.assertFalse(resolved.startswith("https://stage.pokitnote.com"))

    def test_plugin_setting_defaults_to_staging(self):
        plugin = json.loads((ROOT / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
        setting = plugin["variables"]["properties"]["POKITNOTE_API_BASE"]
        self.assertEqual(setting["default"], DEFAULT_API_BASE)
        self.assertEqual(mcp_url(setting["default"]), f"{DEFAULT_API_BASE}/mcp/")
        self.assertEqual(plugin["mcpServers"], "./mcp.json")
        marketplace = json.loads((ROOT / ".cursor-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(marketplace["plugins"][0]["name"], "pokit-note")
        self.assertEqual(marketplace["plugins"][0]["source"], ".")

    def test_connect_steps_use_authenticate(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        skill = (ROOT / "skills" / "pokit-note" / "SKILL.md").read_text(encoding="utf-8")
        command = (ROOT / "commands" / "sign-in.md").read_text(encoding="utf-8")
        plugin = (ROOT / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8")
        marketplace = (ROOT / ".cursor-plugin" / "marketplace.json").read_text(encoding="utf-8")
        for text in (readme, skill, command, plugin, marketplace):
            self.assertIn("Authenticate", text)
            self.assertIn("Allow", text)
        for text in (readme, skill, command):
            lowered = text.lower()
            self.assertIn("sign in on pokit note", lowered)
            self.assertNotIn("mcp_server.py", text)
            self.assertNotIn("python3", lowered)
        self.assertIn("show, create, or edit", skill.lower())
        self.assertIn("notes, lists, and recipes", command.lower())

    def test_local_stdio_server_is_not_shipped(self):
        self.assertFalse((ROOT / "server" / "mcp_server.py").exists())
        self.assertFalse((ROOT / "server" / "connection.py").exists())

    def test_plugin_files_have_no_secrets(self):
        banned = ("CLIENT_SECRET", "pnt_", "pnoa_", "pnor_", "pnoc_", "Bearer ", "api_key", "password")
        paths = [
            ROOT / "mcp.json",
            ROOT / "README.md",
            ROOT / ".cursor-plugin" / "plugin.json",
            ROOT / ".cursor-plugin" / "marketplace.json",
            ROOT / "skills" / "pokit-note" / "SKILL.md",
            ROOT / "commands" / "sign-in.md",
        ]
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for word in banned:
                self.assertNotIn(word, text, msg=f"{path.name} contains {word}")


if __name__ == "__main__":
    unittest.main()
