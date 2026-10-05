import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

import connection
from connection import (
    Connection,
    ConnectionError,
    _accept_tokens,
    _error_message,
    add_list_item,
    api_base,
    authorize_url,
    code_challenge,
    create_list,
    create_note,
    create_recipe,
    describe_entry,
    edit_ingredient,
    edit_list,
    edit_list_item,
    edit_note,
    exchange_code,
    list_lists,
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
        self.assertEqual(api_base("https://example.invalid/"), "https://example.invalid")

    def test_address_must_be_a_web_address(self):
        with self.assertRaises(ConnectionError):
            api_base("file:///tmp/pokitnote")
        with self.assertRaises(ConnectionError):
            api_base("https://user:secret@example.invalid")


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
                "https://example.invalid",
                Connection("pnoa_old", "pnor_keep", 0),
            )
        finally:
            connection._form_request = original
        self.assertEqual(refreshed.refresh_token, "pnor_keep")
        self.assertEqual(refreshed.access_token, "pnoa_new")
        self.assertEqual(seen["url"], "https://example.invalid/oauth/token")
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
            exchange_code("https://example.invalid", "pnoc_code", "http://127.0.0.1:9/callback", new_verifier())
        finally:
            connection._form_request = original
        self.assertEqual(seen["url"], "https://example.invalid/oauth/token")
        self.assertEqual(seen["fields"]["grant_type"], "authorization_code")
        self.assertEqual(seen["fields"]["client_id"], "grok-bot")
        self.assertNotIn("/api/login", seen["url"])


class AuthorizeTests(unittest.TestCase):
    def test_page_uses_the_chosen_address_and_a_loopback_return(self):
        verifier = new_verifier()
        url = authorize_url("https://example.invalid", "http://127.0.0.1:4321/callback", "state-value", verifier)
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        self.assertEqual(parts.scheme, "https")
        self.assertEqual(parts.hostname, "example.invalid")
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

    def test_grocery_items_are_grouped_by_aisle(self):
        text = describe_entry(
            {
                "id": "list-1",
                "kind": "shopping",
                "title": "Store",
                "completed_mode": "cross_off",
                "show_item_lines": False,
                "items": [
                    {"id": "milk", "text": "Milk", "aisle": "Dairy & Eggs", "position": 2},
                    {"id": "apple", "text": "Apples", "aisle": "Fresh Produce", "position": 1},
                    {"id": "tape", "text": "Tape", "position": 3},
                ],
            }
        )
        self.assertIn("Grocery Shopping: Store (list-1)", text)
        self.assertLess(text.index("Tape"), text.index("Fresh Produce"))
        self.assertLess(text.index("Fresh Produce"), text.index("Dairy & Eggs"))
        self.assertIn("Apples (apple)", text)
        self.assertNotIn("flagged", text.lower())

    def test_recipe_shows_group_quantity_and_measurement(self):
        text = describe_entry(
            {
                "kind": "recipe",
                "title": "Pancakes",
                "body": "Best the same day.",
                "instructions": "Whisk, then rest.",
                "ingredients": [
                    {
                        "id": "flour",
                        "text": "flour",
                        "quantity": "1",
                        "measurement": "cup",
                        "group_name": "Dry",
                        "aisle": "Baking & Spices",
                        "position": 1,
                    }
                ],
                "steps": [{"id": "mix", "text": "Mix"}],
            }
        )
        self.assertIn("Notes", text)
        self.assertIn("Best the same day.", text)
        self.assertIn("Instructions", text)
        self.assertIn("Dry", text)
        self.assertIn("flour (flour) — 1 cup, Baking & Spices", text)
        self.assertIn("1. Mix (mix)", text)

    def test_list_summary_names_the_type(self):
        text = summarize_entries(
            [{"id": "one", "title": "Market", "kind": "shopping"}],
            "No lists yet.",
        )
        self.assertEqual(text, "- Market (Grocery Shopping, one)")


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
            [
                "sign_in",
                "sign_out",
                "list_notes",
                "list_lists",
                "list_recipes",
                "open_item",
                "create_note",
                "edit_note",
                "create_list",
                "edit_list",
                "add_list_item",
                "edit_list_item",
                "create_recipe",
                "edit_recipe",
                "add_ingredient",
                "edit_ingredient",
                "add_step",
                "edit_step",
            ],
        )
        blob = json.dumps(response)
        self.assertNotIn("pnt_", blob)
        self.assertNotIn("pnoa_", blob)
        self.assertNotIn("/api/login", blob)
        lowered = blob.lower()
        self.assertNotIn("flagged", lowered)
        self.assertNotIn("due_at", lowered)
        self.assertNotIn("urgent", lowered)

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

    def test_create_note_tool_uses_the_title_and_text(self):
        seen = {}

        def fake_current(base, path=None):
            return Connection("pnoa_access", "pnor_refresh", time.time() + 60)

        def fake_create(base, connection, title, body=""):
            seen["base"] = base
            seen["title"] = title
            seen["body"] = body
            return {"id": "note-1", "kind": "note", "title": title, "body": body}

        previous = os.environ.get("POKITNOTE_API_BASE")
        os.environ["POKITNOTE_API_BASE"] = "https://example.invalid"
        original_current = mcp_server.current_connection
        original_create = mcp_server.create_note
        mcp_server.current_connection = fake_current
        mcp_server.create_note = fake_create
        try:
            response = mcp_server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "create_note", "arguments": {"title": "Hello", "text": "There"}},
                }
            )
        finally:
            mcp_server.current_connection = original_current
            mcp_server.create_note = original_create
            if previous is None:
                os.environ.pop("POKITNOTE_API_BASE", None)
            else:
                os.environ["POKITNOTE_API_BASE"] = previous
        self.assertEqual(seen, {"base": "https://example.invalid", "title": "Hello", "body": "There"})
        text = response["result"]["content"][0]["text"]
        self.assertIn("Note: Hello", text)
        self.assertIn("There", text)
        self.assertFalse(response["result"]["isError"])


class WriteTests(unittest.TestCase):
    def setUp(self):
        self.connection = Connection("pnoa_access", "pnor_refresh", time.time() + 3600)
        self.calls = []
        self.original = connection._read_json
        connection._read_json = self.fake_read

    def tearDown(self):
        connection._read_json = self.original

    def fake_read(self, request):
        body = None
        if request.data:
            raw = request.data.decode("utf-8")
            body = json.loads(raw) if raw[:1] in "{[" else raw
        self.calls.append(
            {
                "method": request.method,
                "url": request.full_url,
                "body": body,
                "authorization": request.get_header("Authorization"),
            }
        )
        url = request.full_url
        if url.endswith("/oauth/token"):
            return {"access_token": "pnoa_new", "expires_in": 3600}
        if "kind=" in url:
            return {"entries": []}
        if url.endswith("/ingredients"):
            if isinstance(body, dict) and body.get("text") == "breaks":
                raise ConnectionError("Pokit Note could not complete that request.")
            return {"id": "ing-1", "text": body.get("text") if isinstance(body, dict) else ""}
        if url.endswith("/steps"):
            return {"id": "step-1", "text": "Mix"}
        if url.endswith("/items"):
            return {"id": "item-1", "text": body.get("text") if isinstance(body, dict) else ""}
        if "/items/" in url and request.method == "PATCH":
            return {"id": "item-1"}
        if request.method == "GET":
            return {
                "id": "saved-1",
                "kind": "note",
                "title": "Hello",
                "body": "There",
                "items": [],
                "ingredients": [],
                "steps": [],
            }
        return {"id": "saved-1", "kind": "note", "title": "Hello", "body": "There"}

    def test_create_note_uses_the_saved_connection(self):
        create_note("https://example.invalid", self.connection, "Hello", "There")
        posted = self.calls[0]
        self.assertEqual(posted["method"], "POST")
        self.assertEqual(posted["url"], "https://example.invalid/api/entries")
        self.assertEqual(posted["body"], {"kind": "note", "title": "Hello", "body": "There"})
        self.assertEqual(posted["authorization"], "Bearer pnoa_access")
        self.assertTrue(all("/api/login" not in call["url"] for call in self.calls))
        self.assertTrue(all(not str(call["authorization"] or "").startswith("Bearer pnt_") for call in self.calls))

    def test_edit_note_sends_only_the_new_text(self):
        edit_note("https://example.invalid", self.connection, "note-1", body="Updated")
        posted = self.calls[0]
        self.assertEqual(posted["method"], "PATCH")
        self.assertEqual(posted["url"], "https://example.invalid/api/entries/note-1")
        self.assertEqual(posted["body"], {"body": "Updated"})

    def test_list_types_use_the_stored_names(self):
        create_list("https://example.invalid", self.connection, "Errands", "List")
        create_list("https://example.invalid", self.connection, "Morning", "Checklist", completed="Hide", lines=True)
        create_list(
            "https://example.invalid",
            self.connection,
            "Store",
            "Grocery Shopping",
            color="Green",
            icon="cart",
        )
        kinds = [call["body"]["kind"] for call in self.calls if call["method"] == "POST"]
        self.assertEqual(kinds, ["todo", "checklist", "shopping"])
        checklist = next(call["body"] for call in self.calls if call["body"] and call["body"].get("title") == "Morning")
        self.assertEqual(checklist["completed_mode"], "hide")
        self.assertIs(checklist["show_item_lines"], True)
        grocery = next(call["body"] for call in self.calls if call["body"] and call["body"].get("title") == "Store")
        self.assertEqual(grocery["color"], "#3d9a78")
        self.assertEqual(grocery["icon"], "cart")

    def test_edit_list_cannot_send_a_new_type(self):
        edit_list("https://example.invalid", self.connection, "list-1", title="Evening", color="Red")
        body = self.calls[0]["body"]
        self.assertEqual(body, {"title": "Evening", "color": "#d64545"})
        self.assertNotIn("kind", body)

    def test_grocery_item_aisle_is_saved_after_the_item(self):
        add_list_item(
            "https://example.invalid",
            self.connection,
            "list-1",
            "Milk",
            aisle="Dairy & Eggs",
        )
        self.assertEqual(self.calls[0]["method"], "POST")
        self.assertEqual(self.calls[0]["url"], "https://example.invalid/api/entries/list-1/items")
        self.assertEqual(self.calls[0]["body"], {"text": "Milk"})
        self.assertEqual(self.calls[1]["method"], "PATCH")
        self.assertEqual(self.calls[1]["url"], "https://example.invalid/api/entries/list-1/items/item-1")
        self.assertEqual(self.calls[1]["body"], {"aisle": "Dairy & Eggs"})

    def test_edit_item_leaves_out_flag_date_and_time(self):
        edit_list_item(
            "https://example.invalid",
            self.connection,
            "list-1",
            "item-1",
            text="Bread",
            checked=True,
            note="The bakery one",
            under="item-9",
        )
        body = self.calls[0]["body"]
        self.assertEqual(
            body,
            {"text": "Bread", "checked": True, "note": "The bakery one", "parent_id": "item-9"},
        )
        self.assertNotIn("flagged", body)
        self.assertNotIn("due_at", body)

    def test_unknown_aisle_is_rejected_before_a_request(self):
        with self.assertRaises(ConnectionError):
            add_list_item("https://example.invalid", self.connection, "list-1", "Milk", aisle="Aisle 7")
        self.assertEqual(self.calls, [])

    def test_recipe_sends_ingredient_groups_then_steps(self):
        create_recipe(
            "https://example.invalid",
            self.connection,
            "Pancakes",
            notes="Best the same day.",
            instructions="Whisk, then rest.",
            ingredients=[
                {
                    "name": "flour",
                    "quantity": "1",
                    "measurement": "cup",
                    "group": "Dry",
                    "aisle": "Baking & Spices",
                }
            ],
            steps=["Mix the dry ingredients"],
        )
        posts = [call for call in self.calls if call["method"] == "POST"]
        self.assertEqual(posts[0]["body"]["kind"], "recipe")
        self.assertEqual(posts[0]["body"]["body"], "Best the same day.")
        self.assertEqual(posts[0]["body"]["instructions"], "Whisk, then rest.")
        self.assertEqual(
            posts[1]["body"],
            {
                "text": "flour",
                "quantity": "1",
                "measurement": "cup",
                "group_name": "Dry",
                "aisle": "Baking & Spices",
            },
        )
        self.assertTrue(posts[1]["url"].endswith("/ingredients"))
        self.assertEqual(posts[2]["body"], {"text": "Mix the dry ingredients"})
        self.assertTrue(posts[2]["url"].endswith("/steps"))

    def test_bad_ingredient_aisle_does_not_create_the_recipe(self):
        with self.assertRaises(ConnectionError):
            create_recipe(
                "https://example.invalid",
                self.connection,
                "Mystery",
                ingredients=[{"name": "flour", "aisle": "Aisle 7"}],
            )
        self.assertEqual(self.calls, [])

    def test_a_failed_ingredient_keeps_the_saved_recipe(self):
        with self.assertRaises(ConnectionError) as caught:
            create_recipe(
                "https://example.invalid",
                self.connection,
                "Soup",
                ingredients=[{"name": "breaks"}],
            )
        self.assertIn("saved-1", str(caught.exception))
        self.assertEqual(self.calls[0]["method"], "POST")
        self.assertTrue(self.calls[0]["url"].endswith("/api/entries"))

    def test_edit_ingredient_can_clear_the_group(self):
        edit_ingredient(
            "https://example.invalid",
            self.connection,
            "recipe-1",
            "ing-1",
            quantity="2",
            group="",
        )
        self.assertEqual(self.calls[0]["body"], {"quantity": "2", "group_name": ""})
        self.assertTrue(self.calls[0]["url"].endswith("/ingredients/ing-1"))

    def test_showing_lists_asks_for_each_list_type(self):
        self.calls.clear()
        list_lists("https://example.invalid", self.connection)
        kinds = [call["url"].rsplit("kind=", 1)[-1] for call in self.calls]
        self.assertEqual(kinds, ["todo", "checklist", "shopping"])

    def test_expired_access_is_refreshed_before_the_change_is_retried(self):
        previous = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as directory:
            os.environ["HOME"] = directory
            try:
                expired = Connection("pnoa_old", "pnor_keep", 0)
                original = connection._read_json

                def fake_read(request):
                    if request.full_url.endswith("/oauth/token"):
                        return {"access_token": "pnoa_new", "expires_in": 3600}
                    if request.get_header("Authorization") == "Bearer pnoa_old":
                        error = ConnectionError("Sign in to Pokit Note again.")
                        error.status = 401
                        raise error
                    self.calls.append(request.get_header("Authorization"))
                    if request.method == "GET":
                        return {"id": "saved-1", "kind": "note", "title": "Hello", "body": ""}
                    return {"id": "saved-1", "kind": "note", "title": "Hello", "body": ""}

                connection._read_json = fake_read
                try:
                    create_note("https://example.invalid", expired, "Hello")
                finally:
                    connection._read_json = original
            finally:
                if previous is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = previous
        self.assertIn("Bearer pnoa_new", self.calls)
        self.assertEqual(expired.access_token, "pnoa_new")

    def test_validation_errors_stay_readable(self):
        message = _error_message(
            json.dumps({"detail": [{"msg": "Value error, Pick an aisle from the list"}]}),
            422,
        )
        self.assertEqual(message, "Pick an aisle from the list")


class SettingFileTests(unittest.TestCase):
    def test_plugin_setting_defaults_to_staging(self):
        root = Path(__file__).resolve().parents[1]
        plugin = json.loads((root / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
        setting = plugin["variables"]["properties"]["POKITNOTE_API_BASE"]
        self.assertEqual(setting["default"], "https://stage.pokitnote.com")
        mcp = json.loads((root / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(mcp["mcpServers"]["pokit-note"]["env"]["POKITNOTE_API_BASE"], "${POKITNOTE_API_BASE}")


if __name__ == "__main__":
    unittest.main()
