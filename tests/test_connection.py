import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

import connection
from connection import (
    Connection,
    ConnectionError,
    _accept_tokens,
    api_base,
    authorize_url,
    code_challenge,
    describe_entry,
    exchange_code,
    load_connection,
    new_verifier,
    refresh_connection,
    save_connection,
    summarize_entries,
)
import mcp_server


class ApiBaseTests(unittest.TestCase):
    def test_empty_setting_uses_staging(self):
        self.assertEqual(api_base(""), "https://stage.pokitnote.com")
        self.assertEqual(api_base("${POKITNOTE_API_BASE}"), "https://stage.pokitnote.com")

    def test_custom_address_is_kept(self):
        self.assertEqual(api_base("https://notes.example.com/"), "https://notes.example.com")

    def test_address_must_be_a_web_address(self):
        with self.assertRaises(ConnectionError):
            api_base("file:///tmp/pokitnote")
        with self.assertRaises(ConnectionError):
            api_base("https://user:secret@notes.example.com")


class TokenTests(unittest.TestCase):
    def test_phone_key_is_refused(self):
        with self.assertRaises(ConnectionError):
            _accept_tokens({"access_token": "pnt_phone", "refresh_token": "pnor_bot", "expires_in": 3600})

    def test_saved_phone_key_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "connection.json"
            path.write_text(json.dumps({"access_token": "pnt_phone", "refresh_token": "pnor_bot"}), encoding="utf-8")
            with self.assertRaises(ConnectionError):
                load_connection(path)
            self.assertFalse(path.exists())

    def test_refresh_keeps_the_same_refresh_token(self):
        seen = {}

        def fake_form(url, fields):
            seen["url"] = url
            seen["fields"] = fields
            return {"access_token": "pnoa_new", "expires_in": 3600}

        original = connection._form_request
        connection._form_request = fake_form
        try:
            refreshed = refresh_connection(
                "https://notes.example.com",
                Connection("pnoa_old", "pnor_keep", 0),
            )
        finally:
            connection._form_request = original
        self.assertEqual(refreshed.refresh_token, "pnor_keep")
        self.assertEqual(refreshed.access_token, "pnoa_new")
        self.assertEqual(seen["url"], "https://notes.example.com/oauth/token")
        self.assertEqual(seen["fields"]["grant_type"], "refresh_token")
        self.assertNotIn("api/login", seen["url"])

    def test_sign_in_exchange_uses_the_chosen_address(self):
        seen = {}

        def fake_form(url, fields):
            seen["url"] = url
            seen["fields"] = fields
            return {"access_token": "pnoa_access", "refresh_token": "pnor_refresh", "expires_in": 3600}

        original = connection._form_request
        connection._form_request = fake_form
        try:
            exchange_code("https://notes.example.com", "pnoc_code", "http://127.0.0.1:9/callback", new_verifier())
        finally:
            connection._form_request = original
        self.assertEqual(seen["url"], "https://notes.example.com/oauth/token")
        self.assertEqual(seen["fields"]["grant_type"], "authorization_code")
        self.assertEqual(seen["fields"]["client_id"], "grok-bot")
        self.assertNotIn("/api/login", seen["url"])


class AuthorizeTests(unittest.TestCase):
    def test_page_uses_the_chosen_address_and_a_loopback_return(self):
        verifier = new_verifier()
        url = authorize_url("https://notes.example.com", "http://127.0.0.1:4321/callback", "state-value", verifier)
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        self.assertEqual(parts.scheme, "https")
        self.assertEqual(parts.hostname, "notes.example.com")
        self.assertEqual(parts.path, "/oauth/authorize")
        self.assertEqual(query["client_id"], ["grok-bot"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["code_challenge"], [code_challenge(verifier)])
        self.assertTrue(query["redirect_uri"][0].startswith("http://127.0.0.1:"))


class DisplayTests(unittest.TestCase):
    def test_empty_notes(self):
        self.assertEqual(summarize_entries([], "No notes yet."), "No notes yet.")

    def test_recipe_text(self):
        text = describe_entry(
            {
                "kind": "recipe",
                "title": "Soup",
                "ingredients": [{"text": "Broth"}],
                "steps": [{"text": "Simmer"}],
            }
        )
        self.assertIn("Recipe: Soup", text)
        self.assertIn("Broth", text)
        self.assertIn("Simmer", text)


class StoreTests(unittest.TestCase):
    def test_connection_file_is_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "connection.json"
            save_connection(Connection("pnoa_access", "pnor_refresh", 10), path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            loaded = load_connection(path)
            self.assertEqual(loaded.access_token, "pnoa_access")


class ToolListTests(unittest.TestCase):
    def test_tools_are_listed_in_plain_language(self):
        response = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = [tool["name"] for tool in response["result"]["tools"]]
        self.assertEqual(
            names,
            ["sign_in", "sign_out", "list_notes", "list_lists", "list_recipes", "open_item"],
        )
        blob = json.dumps(response)
        self.assertNotIn("pnt_", blob)
        self.assertNotIn("pnoa_", blob)
        self.assertNotIn("/api/login", blob)

    def test_sign_out_without_a_connection(self):
        previous = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as directory:
            os.environ["HOME"] = directory
            try:
                response = mcp_server.handle(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "sign_out", "arguments": {}},
                    }
                )
            finally:
                if previous is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = previous
        text = response["result"]["content"][0]["text"]
        self.assertIn("not connected", text)


if __name__ == "__main__":
    unittest.main()
