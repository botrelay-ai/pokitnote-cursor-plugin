"""Pokit Note connection for Grok Bot.

The person signs in on the Pokit Note page. This stores the connection that
page returns. It never calls the phone sign-in and never keeps a phone key.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DEFAULT_API_BASE = "https://stage.pokitnote.com"
CLIENT_ID = "grok-bot"
PHONE_KEY_PREFIX = "pnt_"
ACCESS_PREFIX = "pnoa_"
REFRESH_PREFIX = "pnor_"

TITLE_MAX = 200
BODY_MAX = 20_000
ITEM_MAX = 500
NOTE_MAX = 20_000
STEP_MAX = 2000
QUANTITY_MAX = 40
MEASUREMENT_MAX = 40
GROUP_MAX = 80

# Stored values from the Pokit Note app. Plain names are what a person says.
COLORS = (
    "#88c3ed",
    "#145a86",
    "#3d9a78",
    "#e39b4a",
    "#d64545",
    "#7c6bb0",
)
COLOR_NAMES = {
    "sky blue": "#88c3ed",
    "deep blue": "#145a86",
    "green": "#3d9a78",
    "orange": "#e39b4a",
    "red": "#d64545",
    "purple": "#7c6bb0",
}
COLOR_LABELS = {value: name for name, value in COLOR_NAMES.items()}

# Icon names the app offers, plus older names a saved list can still use.
ICONS = (
    "face.smiling",
    "list.bullet",
    "bookmark",
    "key",
    "gift",
    "birthday.cake",
    "graduationcap",
    "backpack",
    "ruler",
    "doc",
    "books.vertical",
    "wallet.pass",
    "creditcard",
    "banknote",
    "dumbbell",
    "figure.run",
    "fork.knife",
    "wineglass",
    "pills",
    "stethoscope",
    "chair",
    "house",
    "building.2",
    "building.columns",
    "tent",
    "desktopcomputer",
    "music.note",
    "tv",
    "gamecontroller",
    "headphones",
    "leaf",
    "carrot",
    "person",
    "person.2",
    "person.3",
    "pawprint",
    "teddybear",
    "fish",
    "basket",
    "cart",
    "bag",
    "shippingbox",
    "soccerball",
    "baseball",
    "basketball",
    "football",
    "tennis.racket",
    "train.side.front.car",
    "airplane",
    "sailboat",
    "car",
    "umbrella",
    "sun.max",
    "moon",
    "drop",
    "snowflake",
    "flame",
    "briefcase",
    "wrench",
    "scissors",
    "pencil.and.ruler",
    "curlybraces",
    "lightbulb",
    "bubble.left",
    "shoeprints.fill",
    "asterisk",
    "square",
    "circle",
    "triangle",
    "diamond",
    "heart",
    "star",
    "checklist",
    "flag",
    "book",
)

AISLES = (
    "Fresh Produce",
    "Meat and Fish",
    "Pharmacy",
    "Bakery",
    "Flower Shop",
    "Wine & Beer",
    "Breakfast & Cereal",
    "Baking & Spices",
    "Canned Goods & Soup",
    "Pasta, Rice & Sauces",
    "Snacks & Crackers",
    "Beverages",
    "Dairy & Eggs",
    "Frozen Foods",
)

LIST_TYPES = {
    "list": "todo",
    "checklist": "checklist",
    "grocery shopping": "shopping",
}
KIND_LABELS = {
    "note": "Note",
    "todo": "List",
    "checklist": "Checklist",
    "shopping": "Grocery Shopping",
    "recipe": "Recipe",
}
LIST_KINDS = ("todo", "checklist", "shopping")


class ConnectionError(Exception):
    """A problem the person can act on. The message is safe to show."""


@dataclass
class Connection:
    access_token: str
    refresh_token: str
    expires_at: float


def api_base(raw: str | None = None) -> str:
    """Return the Pokit Note address. An empty setting uses staging."""
    value = (raw if raw is not None else os.environ.get("POKITNOTE_API_BASE", "")).strip()
    if not value or value.startswith("${"):
        value = DEFAULT_API_BASE
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ConnectionError("The Pokit Note address needs to be a web address.")
    if parsed.username or parsed.password:
        raise ConnectionError("The Pokit Note address should not include a name or password.")
    return value.rstrip("/")


def store_path() -> Path:
    return Path.home() / ".pokitnote" / "grok-bot-connection.json"


def code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def new_verifier() -> str:
    return secrets.token_urlsafe(32)


def authorize_url(base: str, redirect_uri: str, state: str, verifier: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": CLIENT_ID,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "code_challenge": code_challenge(verifier),
            "code_challenge_method": "S256",
        }
    )
    return f"{base}/oauth/authorize?{query}"


def _reject_phone_key(token: str) -> None:
    if token.startswith(PHONE_KEY_PREFIX):
        raise ConnectionError(
            "Pokit Note offered the key from the iPhone app. This connection will not use it."
        )


def _accept_tokens(body: dict, previous_refresh: str = "") -> Connection:
    access = str(body.get("access_token") or "")
    refresh = str(body.get("refresh_token") or previous_refresh)
    _reject_phone_key(access)
    _reject_phone_key(refresh)
    if not access.startswith(ACCESS_PREFIX) or not refresh.startswith(REFRESH_PREFIX):
        raise ConnectionError("Pokit Note did not return a Grok Bot connection. Nothing was saved.")
    expires_in = int(body.get("expires_in") or 3600)
    return Connection(access, refresh, time.time() + max(expires_in - 60, 30))


def load_connection(path: Path | None = None) -> Connection | None:
    file = path or store_path()
    if not file.is_file():
        return None
    try:
        body = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConnectionError("The saved Pokit Note connection could not be read.") from exc
    access = str(body.get("access_token") or "")
    refresh = str(body.get("refresh_token") or "")
    if access.startswith(PHONE_KEY_PREFIX) or refresh.startswith(PHONE_KEY_PREFIX):
        file.unlink(missing_ok=True)
        raise ConnectionError("A phone key was saved here. It has been removed. Sign in again.")
    if not access.startswith(ACCESS_PREFIX) or not refresh.startswith(REFRESH_PREFIX):
        return None
    return Connection(access, refresh, float(body.get("expires_at") or 0))


def save_connection(connection: Connection, path: Path | None = None) -> None:
    _reject_phone_key(connection.access_token)
    _reject_phone_key(connection.refresh_token)
    file = path or store_path()
    file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "access_token": connection.access_token,
        "refresh_token": connection.refresh_token,
        "expires_at": connection.expires_at,
    }
    file.write_text(json.dumps(payload), encoding="utf-8")
    file.chmod(0o600)


def clear_connection(path: Path | None = None) -> None:
    file = path or store_path()
    file.unlink(missing_ok=True)


def _form_request(url: str, fields: dict[str, str]) -> dict:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    return _read_json(request)


def _read_json(request: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        message = _error_message(detail, exc.code)
        error = ConnectionError(message)
        error.status = exc.code  # type: ignore[attr-defined]
        raise error from exc
    except urllib.error.URLError as exc:
        raise ConnectionError("Pokit Note could not be reached. Check the Pokit Note address.") from exc
    if not raw:
        return {}
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConnectionError("Pokit Note sent a response that could not be read.") from exc
    if not isinstance(body, dict):
        raise ConnectionError("Pokit Note sent a response that could not be read.")
    return body


def _error_message(detail: str, status: int) -> str:
    try:
        body = json.loads(detail)
    except json.JSONDecodeError:
        body = {}
    if isinstance(body, dict):
        text = body.get("error_description") or body.get("detail") or ""
        if isinstance(text, str) and text.strip():
            return text.strip()
        if isinstance(text, list):
            messages = [_detail_row(row) for row in text]
            messages = [message for message in messages if message]
            if messages:
                return " ".join(messages)
    if status == 401:
        return "Sign in to Pokit Note again."
    return "Pokit Note could not complete that request."


def _detail_row(row: object) -> str:
    if isinstance(row, str):
        return row.strip()
    if not isinstance(row, dict):
        return ""
    msg = row.get("msg")
    if not isinstance(msg, str):
        return ""
    cleaned = msg.strip()
    prefix = "Value error, "
    if cleaned.startswith(prefix):
        cleaned = cleaned[len(prefix) :].strip()
    return cleaned


def exchange_code(base: str, code: str, redirect_uri: str, verifier: str) -> Connection:
    body = _form_request(
        f"{base}/oauth/token",
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": CLIENT_ID,
            "code_verifier": verifier,
        },
    )
    return _accept_tokens(body)


def refresh_connection(base: str, connection: Connection) -> Connection:
    body = _form_request(
        f"{base}/oauth/token",
        {
            "grant_type": "refresh_token",
            "refresh_token": connection.refresh_token,
            "client_id": CLIENT_ID,
        },
    )
    return _accept_tokens(body, previous_refresh=connection.refresh_token)


def revoke_connection(base: str, connection: Connection) -> None:
    _form_request(
        f"{base}/oauth/revoke",
        {"token": connection.refresh_token, "client_id": CLIENT_ID},
    )


class _Callback(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != "/callback":
            self._reply(404, "That page is not part of sign-in.")
            return
        query = urllib.parse.parse_qs(parsed.query)
        self.server.query = {key: values[0] for key, values in query.items() if values}  # type: ignore[attr-defined]
        self._reply(200, "You can close this page and return to Grok Bot.")

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _reply(self, status: int, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def wait_for_sign_in(base: str, timeout: float = 300, on_url=None) -> tuple[str, Connection]:
    """Open the Pokit Note page and wait until the person allows access."""
    verifier = new_verifier()
    state = secrets.token_urlsafe(24)
    server = HTTPServer(("127.0.0.1", 0), _Callback)
    server.query = {}  # type: ignore[attr-defined]
    port = server.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    url = authorize_url(base, redirect_uri, state, verifier)
    if on_url is not None:
        on_url(url)
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:
        pass
    server.timeout = timeout
    server.handle_request()
    query = server.query  # type: ignore[attr-defined]
    server.server_close()
    if not query:
        raise ConnectionError("Sign-in was not finished. Open Pokit Note and try again.")
    if query.get("state") != state:
        raise ConnectionError("That sign-in did not match this one. Try again.")
    if query.get("error"):
        raise ConnectionError("Pokit Note was not allowed. Sign in again if you still want Grok Bot to connect.")
    code = query.get("code") or ""
    if not code:
        raise ConnectionError("Pokit Note did not finish sign-in. Try again.")
    return url, exchange_code(base, code, redirect_uri, verifier)


def current_connection(base: str, path: Path | None = None) -> Connection:
    connection = load_connection(path)
    if connection is None:
        raise ConnectionError("Sign in to Pokit Note first.")
    if connection.expires_at > time.time():
        return connection
    refreshed = refresh_connection(base, connection)
    save_connection(refreshed, path)
    return refreshed


def _remember(connection: Connection, refreshed: Connection) -> None:
    connection.access_token = refreshed.access_token
    connection.refresh_token = refreshed.refresh_token
    connection.expires_at = refreshed.expires_at


def api_json(base: str, connection: Connection, method: str, path: str, payload: dict | None = None) -> dict:
    """Call Pokit Note with the saved connection. A phone key is never sent."""
    _reject_phone_key(connection.access_token)

    def call(token: str) -> dict:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(f"{base}{path}", data=data, method=method, headers=headers)
        return _read_json(request)

    try:
        return call(connection.access_token)
    except ConnectionError as exc:
        if getattr(exc, "status", None) != 401:
            raise
        refreshed = refresh_connection(base, connection)
        save_connection(refreshed)
        _remember(connection, refreshed)
        return call(connection.access_token)


def api_get(base: str, connection: Connection, path: str) -> dict:
    return api_json(base, connection, "GET", path)


def list_kind(base: str, connection: Connection, kind: str) -> list[dict]:
    body = api_get(base, connection, f"/api/entries?kind={urllib.parse.quote(kind)}")
    entries = body.get("entries")
    if not isinstance(entries, list):
        raise ConnectionError("Pokit Note did not return your items.")
    return [item for item in entries if isinstance(item, dict)]


def list_lists(base: str, connection: Connection) -> list[dict]:
    rows: list[dict] = []
    for kind in LIST_KINDS:
        rows.extend(list_kind(base, connection, kind))
    rows.sort(key=lambda entry: str(entry.get("updated_at") or ""), reverse=True)
    return rows


def open_entry(base: str, connection: Connection, entry_id: str) -> dict:
    cleaned = _identifier(entry_id, "Choose a note, list, or recipe first.")
    return api_get(base, connection, f"/api/entries/{urllib.parse.quote(cleaned, safe='')}")


def _open_saved(base: str, connection: Connection, entry_id: str) -> dict:
    try:
        return open_entry(base, connection, entry_id)
    except ConnectionError as exc:
        raise ConnectionError(f"It was saved ({entry_id.strip()}), but it could not be opened again. {exc}") from exc


def _reload(base: str, connection: Connection, created: dict) -> dict:
    entry_id = str(created.get("id") or "").strip()
    if not entry_id:
        raise ConnectionError("Pokit Note did not return that item.")
    return _open_saved(base, connection, entry_id)


def _identifier(value: str, missing: str) -> str:
    if not isinstance(value, str):
        raise ConnectionError("That needs to be text.")
    cleaned = value.strip()
    if not cleaned:
        raise ConnectionError(missing)
    return cleaned


def _entry_path(entry_id: str) -> str:
    return f"/api/entries/{urllib.parse.quote(_identifier(entry_id, 'Choose a note, list, or recipe first.'), safe='')}"


def _bounded(value: str, limit: int, empty: str, too_long: str, required: bool) -> str:
    if not isinstance(value, str):
        raise ConnectionError("That needs to be text.")
    text = value.strip()
    if required and not text:
        raise ConnectionError(empty)
    if len(text) > limit:
        raise ConnectionError(too_long)
    return text


def _title(value: str) -> str:
    return _bounded(value, TITLE_MAX, "Enter a name.", f"A name must be {TITLE_MAX} characters or less.", True)


def _body(value: str, too_long: str) -> str:
    return _bounded(value, BODY_MAX, "", too_long, False)


def _color(value: str) -> str:
    if not isinstance(value, str):
        raise ConnectionError("That needs to be text.")
    text = " ".join(value.strip().lower().split())
    named = COLOR_NAMES.get(text)
    if named:
        return named
    if not text.startswith("#"):
        text = f"#{text}"
    if text not in COLORS:
        raise ConnectionError("Pick a color Pokit Note uses.")
    return text


def _icon(value: str) -> str:
    if not isinstance(value, str):
        raise ConnectionError("That needs to be text.")
    text = value.strip()
    if text not in ICONS:
        raise ConnectionError("Pick an icon Pokit Note uses.")
    return text


def _completed(value: str) -> str:
    if not isinstance(value, str):
        raise ConnectionError("That needs to be text.")
    key = " ".join(value.strip().lower().split())
    mapped = {"cross off": "cross_off", "cross_off": "cross_off", "hide": "hide"}
    if key not in mapped:
        raise ConnectionError("Pick Cross Off or Hide.")
    return mapped[key]


def _list_type(value: str) -> str:
    if not isinstance(value, str):
        raise ConnectionError("That needs to be text.")
    key = " ".join(value.strip().lower().split())
    if key not in LIST_TYPES:
        raise ConnectionError("Pick List, Checklist, or Grocery Shopping.")
    return LIST_TYPES[key]


def _aisle(value: str) -> str:
    if not isinstance(value, str):
        raise ConnectionError("That needs to be text.")
    text = value.strip()
    if not text:
        return ""
    if text not in AISLES:
        raise ConnectionError("Pick an aisle from the grocery list.")
    return text


def _checked(value: bool) -> bool:
    if not isinstance(value, bool):
        raise ConnectionError("That needs to be yes or no.")
    return value


def _lines(value: bool) -> bool:
    if not isinstance(value, bool):
        raise ConnectionError("Lines need to be on or off.")
    return value


def _apply_choices(payload: dict, color: str | None, icon: str | None, completed: str | None, lines: bool | None) -> None:
    if color is not None:
        payload["color"] = _color(color)
    if icon is not None:
        payload["icon"] = _icon(icon)
    if completed is not None:
        payload["completed_mode"] = _completed(completed)
    if lines is not None:
        payload["show_item_lines"] = _lines(lines)


def create_note(base: str, connection: Connection, title: str, body: str = "") -> dict:
    payload = {"kind": "note", "title": _title(title), "body": _body(body or "", f"Text must be {BODY_MAX} characters or less.")}
    return _reload(base, connection, api_json(base, connection, "POST", "/api/entries", payload))


def edit_note(base: str, connection: Connection, entry_id: str, title: str | None = None, body: str | None = None) -> dict:
    fields: dict = {}
    if title is not None:
        fields["title"] = _title(title)
    if body is not None:
        fields["body"] = _body(body, f"Text must be {BODY_MAX} characters or less.")
    if not fields:
        raise ConnectionError("Say what to change.")
    api_json(base, connection, "PATCH", _entry_path(entry_id), fields)
    return _open_saved(base, connection, entry_id)


def create_list(
    base: str,
    connection: Connection,
    title: str,
    list_type: str,
    color: str | None = None,
    icon: str | None = None,
    completed: str | None = None,
    lines: bool | None = None,
) -> dict:
    payload: dict = {"kind": _list_type(list_type), "title": _title(title)}
    _apply_choices(payload, color, icon, completed, lines)
    return _reload(base, connection, api_json(base, connection, "POST", "/api/entries", payload))


def edit_list(
    base: str,
    connection: Connection,
    entry_id: str,
    title: str | None = None,
    color: str | None = None,
    icon: str | None = None,
    completed: str | None = None,
    lines: bool | None = None,
) -> dict:
    fields: dict = {}
    if title is not None:
        fields["title"] = _title(title)
    _apply_choices(fields, color, icon, completed, lines)
    if not fields:
        raise ConnectionError("Say what to change.")
    api_json(base, connection, "PATCH", _entry_path(entry_id), fields)
    return _open_saved(base, connection, entry_id)


def _item_extra(aisle: str | None, under: str | None) -> dict:
    extra: dict = {}
    if aisle is not None:
        extra["aisle"] = _aisle(aisle)
    if under is not None:
        if not isinstance(under, str):
            raise ConnectionError("That needs to be text.")
        extra["parent_id"] = under.strip() or None
    return extra


def add_list_item(
    base: str,
    connection: Connection,
    entry_id: str,
    text: str,
    aisle: str | None = None,
    under: str | None = None,
) -> dict:
    path = _entry_path(entry_id)
    extra = _item_extra(aisle, under)
    item = api_json(
        base,
        connection,
        "POST",
        f"{path}/items",
        {"text": _bounded(text, ITEM_MAX, "Enter an item.", f"An item must be {ITEM_MAX} characters or less.", True)},
    )
    if extra:
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            raise ConnectionError("The item was added, but Pokit Note did not return it.")
        try:
            api_json(base, connection, "PATCH", f"{path}/items/{urllib.parse.quote(item_id, safe='')}", extra)
        except ConnectionError as exc:
            raise ConnectionError(f"The item was added ({item_id}), but part of it could not be saved. {exc}") from exc
    return _open_saved(base, connection, entry_id)


def edit_list_item(
    base: str,
    connection: Connection,
    entry_id: str,
    item_id: str,
    text: str | None = None,
    checked: bool | None = None,
    note: str | None = None,
    aisle: str | None = None,
    under: str | None = None,
) -> dict:
    fields: dict = {}
    if text is not None:
        fields["text"] = _bounded(text, ITEM_MAX, "Enter an item.", f"An item must be {ITEM_MAX} characters or less.", True)
    if checked is not None:
        fields["checked"] = _checked(checked)
    if note is not None:
        fields["note"] = _bounded(note, NOTE_MAX, "", f"A note must be {NOTE_MAX} characters or less.", False)
    fields.update(_item_extra(aisle, under))
    if not fields:
        raise ConnectionError("Say what to change.")
    path = _entry_path(entry_id)
    cleaned_item = _identifier(item_id, "Choose an item first.")
    api_json(base, connection, "PATCH", f"{path}/items/{urllib.parse.quote(cleaned_item, safe='')}", fields)
    return _open_saved(base, connection, entry_id)


def _ingredient_payload(row: object) -> dict:
    if not isinstance(row, dict):
        raise ConnectionError("Each ingredient needs a name.")
    name = row.get("name", row.get("text"))
    quantity = row.get("quantity") or ""
    measurement = row.get("measurement") or ""
    group = row.get("group") or row.get("group_name") or ""
    aisle = row.get("aisle") or ""
    if not isinstance(quantity, str) or not isinstance(measurement, str) or not isinstance(group, str) or not isinstance(aisle, str):
        raise ConnectionError("That needs to be text.")
    if not isinstance(name, str):
        raise ConnectionError("Each ingredient needs a name.")
    return {
        "text": _bounded(name, ITEM_MAX, "Enter an ingredient.", f"An ingredient must be {ITEM_MAX} characters or less.", True),
        "quantity": _bounded(quantity, QUANTITY_MAX, "", f"A quantity must be {QUANTITY_MAX} characters or less.", False),
        "measurement": _bounded(measurement, MEASUREMENT_MAX, "", f"A measurement must be {MEASUREMENT_MAX} characters or less.", False),
        "group_name": _bounded(group, GROUP_MAX, "", f"A group must be {GROUP_MAX} characters or less.", False),
        "aisle": _aisle(aisle),
    }


def _ingredient_changes(name: str | None, quantity: str | None, measurement: str | None, group: str | None, aisle: str | None, checked: bool | None) -> dict:
    fields: dict = {}
    if name is not None:
        fields["text"] = _bounded(name, ITEM_MAX, "Enter an ingredient.", f"An ingredient must be {ITEM_MAX} characters or less.", True)
    if quantity is not None:
        fields["quantity"] = _bounded(quantity, QUANTITY_MAX, "", f"A quantity must be {QUANTITY_MAX} characters or less.", False)
    if measurement is not None:
        fields["measurement"] = _bounded(measurement, MEASUREMENT_MAX, "", f"A measurement must be {MEASUREMENT_MAX} characters or less.", False)
    if group is not None:
        fields["group_name"] = _bounded(group, GROUP_MAX, "", f"A group must be {GROUP_MAX} characters or less.", False)
    if aisle is not None:
        fields["aisle"] = _aisle(aisle)
    if checked is not None:
        fields["checked"] = _checked(checked)
    return fields


def create_recipe(
    base: str,
    connection: Connection,
    title: str,
    notes: str | None = None,
    instructions: str | None = None,
    color: str | None = None,
    icon: str | None = None,
    ingredients: list | None = None,
    steps: list | None = None,
) -> dict:
    ingredient_rows = [_ingredient_payload(row) for row in (ingredients or [])]
    step_rows = [
        _bounded(step, STEP_MAX, "Enter a step.", f"A step must be {STEP_MAX} characters or less.", True)
        if isinstance(step, str)
        else _reject_step()
        for step in (steps or [])
    ]
    payload: dict = {
        "kind": "recipe",
        "title": _title(title),
        "body": _body(notes or "", f"Text must be {BODY_MAX} characters or less."),
        "instructions": _body(instructions or "", f"Instructions must be {BODY_MAX} characters or less."),
    }
    _apply_choices(payload, color, icon, None, None)
    created = api_json(base, connection, "POST", "/api/entries", payload)
    entry_id = str(created.get("id") or "").strip()
    if not entry_id:
        raise ConnectionError("Pokit Note did not return the recipe.")
    path = _entry_path(entry_id)
    try:
        for row in ingredient_rows:
            api_json(base, connection, "POST", f"{path}/ingredients", row)
        for step in step_rows:
            api_json(base, connection, "POST", f"{path}/steps", {"text": step})
    except ConnectionError as exc:
        raise ConnectionError(f"The recipe was saved ({entry_id}), but part of it could not be added. {exc}") from exc
    return _open_saved(base, connection, entry_id)


def _reject_step() -> str:
    raise ConnectionError("Each step needs text.")


def edit_recipe(
    base: str,
    connection: Connection,
    entry_id: str,
    title: str | None = None,
    notes: str | None = None,
    instructions: str | None = None,
    color: str | None = None,
    icon: str | None = None,
) -> dict:
    fields: dict = {}
    if title is not None:
        fields["title"] = _title(title)
    if notes is not None:
        fields["body"] = _body(notes, f"Text must be {BODY_MAX} characters or less.")
    if instructions is not None:
        fields["instructions"] = _body(instructions, f"Instructions must be {BODY_MAX} characters or less.")
    _apply_choices(fields, color, icon, None, None)
    if not fields:
        raise ConnectionError("Say what to change.")
    api_json(base, connection, "PATCH", _entry_path(entry_id), fields)
    return _open_saved(base, connection, entry_id)


def add_ingredient(
    base: str,
    connection: Connection,
    entry_id: str,
    name: str,
    quantity: str = "",
    measurement: str = "",
    group: str = "",
    aisle: str = "",
) -> dict:
    path = _entry_path(entry_id)
    api_json(
        base,
        connection,
        "POST",
        f"{path}/ingredients",
        _ingredient_payload(
            {"name": name, "quantity": quantity, "measurement": measurement, "group": group, "aisle": aisle}
        ),
    )
    return _open_saved(base, connection, entry_id)


def edit_ingredient(
    base: str,
    connection: Connection,
    entry_id: str,
    ingredient_id: str,
    name: str | None = None,
    quantity: str | None = None,
    measurement: str | None = None,
    group: str | None = None,
    aisle: str | None = None,
    checked: bool | None = None,
) -> dict:
    fields = _ingredient_changes(name, quantity, measurement, group, aisle, checked)
    if not fields:
        raise ConnectionError("Say what to change.")
    path = _entry_path(entry_id)
    cleaned = _identifier(ingredient_id, "Choose an ingredient first.")
    api_json(base, connection, "PATCH", f"{path}/ingredients/{urllib.parse.quote(cleaned, safe='')}", fields)
    return _open_saved(base, connection, entry_id)


def add_step(base: str, connection: Connection, entry_id: str, text: str) -> dict:
    path = _entry_path(entry_id)
    api_json(
        base,
        connection,
        "POST",
        f"{path}/steps",
        {"text": _bounded(text, STEP_MAX, "Enter a step.", f"A step must be {STEP_MAX} characters or less.", True)},
    )
    return _open_saved(base, connection, entry_id)


def edit_step(base: str, connection: Connection, entry_id: str, step_id: str, text: str) -> dict:
    path = _entry_path(entry_id)
    cleaned = _identifier(step_id, "Choose a step first.")
    api_json(
        base,
        connection,
        "PATCH",
        f"{path}/steps/{urllib.parse.quote(cleaned, safe='')}",
        {"text": _bounded(text, STEP_MAX, "Enter a step.", f"A step must be {STEP_MAX} characters or less.", True)},
    )
    return _open_saved(base, connection, entry_id)


def summarize_entries(entries: list[dict], empty: str) -> str:
    if not entries:
        return empty
    lines = []
    for entry in entries[:100]:
        title = str(entry.get("title") or "Untitled").replace("\n", " ")
        identifier = str(entry.get("id") or "")
        kind = str(entry.get("kind") or "")
        label = KIND_LABELS.get(kind, "")
        if kind in LIST_KINDS and label and identifier:
            lines.append(f"- {title} ({label}, {identifier})")
        elif identifier:
            lines.append(f"- {title} ({identifier})")
        else:
            lines.append(f"- {title}")
    if len(entries) > 100:
        lines.append("Some items were left out.")
    return "\n".join(lines)


def _color_label(value: str) -> str:
    name = COLOR_LABELS.get(value.strip().lower())
    if not name:
        return value
    return name[:1].upper() + name[1:]


def _item_lines(row: dict, indent: str = "") -> list[str]:
    name = str(row.get("text") or row.get("name") or "Untitled").replace("\n", " ")
    identifier = str(row.get("id") or "").strip()
    line = f"{indent}- {name}"
    if identifier:
        line += f" ({identifier})"
    extras = []
    if row.get("checked"):
        extras.append("checked")
    aisle = str(row.get("aisle") or "").strip()
    if aisle and aisle in AISLES:
        extras.append(aisle)
    if extras:
        line += " — " + ", ".join(extras)
    lines = [line]
    note = str(row.get("note") or "").strip()
    if note:
        lines.append(f"{indent}  {note[:2000]}")
    return lines


def _describe_items(rows: list[dict], grocery: bool) -> list[str]:
    ordered = sorted(rows, key=lambda item: item.get("position") or 0)
    if len(ordered) > 100:
        ordered = ordered[:100]
        clipped = True
    else:
        clipped = len(rows) > 100
    if grocery:
        grouped = {aisle: [] for aisle in AISLES}
        loose = []
        for row in ordered:
            aisle = str(row.get("aisle") or "").strip()
            if aisle in grouped:
                grouped[aisle].append(row)
            else:
                loose.append(row)
        lines: list[str] = []
        for row in loose:
            lines.extend(_item_lines(row))
        for aisle in AISLES:
            section = grouped[aisle]
            if not section:
                continue
            lines.append(aisle)
            for row in section:
                lines.extend(_item_lines(row))
    else:
        ids = {str(row.get("id") or "") for row in ordered}
        children: dict[str, list[dict]] = {}
        tops = []
        for row in ordered:
            parent = str(row.get("parent_id") or "")
            if parent and parent in ids:
                children.setdefault(parent, []).append(row)
            else:
                tops.append(row)
        lines = []
        for row in tops:
            lines.extend(_item_lines(row))
            for child in children.get(str(row.get("id") or ""), []):
                lines.extend(_item_lines(child, indent="  "))
    if clipped:
        lines.append("Some items were left out.")
    return lines


def _describe_ingredients(rows: list[dict]) -> list[str]:
    ordered = sorted(rows, key=lambda item: item.get("position") or 0)[:100]
    blocks: list[tuple[str, list[dict]]] = []
    index: dict[str, int] = {}
    for row in ordered:
        title = str(row.get("group_name") or row.get("group") or "").strip()
        key = title.casefold()
        if key not in index:
            index[key] = len(blocks)
            blocks.append((title, []))
        blocks[index[key]][1].append(row)
    lines = []
    for title, group_rows in blocks:
        if title:
            lines.append(title)
        for row in group_rows:
            name = str(row.get("text") or row.get("name") or "Untitled").replace("\n", " ")
            identifier = str(row.get("id") or "").strip()
            line = f"- {name}"
            if identifier:
                line += f" ({identifier})"
            detail = " ".join(
                part
                for part in (
                    str(row.get("quantity") or "").strip(),
                    str(row.get("measurement") or "").strip(),
                )
                if part
            )
            extras = []
            if detail:
                extras.append(detail)
            aisle = str(row.get("aisle") or "").strip()
            if aisle:
                extras.append(aisle)
            if row.get("checked"):
                extras.append("checked")
            if extras:
                line += " — " + ", ".join(extras)
            lines.append(line)
    if len(rows) > 100:
        lines.append("Some ingredients were left out.")
    return lines


def describe_entry(entry: dict) -> str:
    title = str(entry.get("title") or "Untitled")
    kind = str(entry.get("kind") or "")
    label = KIND_LABELS.get(kind, "Item")
    identifier = str(entry.get("id") or "").strip()
    head = f"{label}: {title}"
    if identifier:
        head += f" ({identifier})"
    lines = [head]
    if kind in {*LIST_KINDS, "recipe"}:
        color = str(entry.get("color") or "").strip()
        icon = str(entry.get("icon") or "").strip()
        if color:
            lines.append(f"Color: {_color_label(color)}")
        if icon:
            lines.append(f"Icon: {icon}")
    if kind in LIST_KINDS:
        mode = str(entry.get("completed_mode") or "")
        if mode == "hide":
            lines.append("Completed items: Hide")
        elif mode == "cross_off":
            lines.append("Completed items: Cross Off")
        if "show_item_lines" in entry:
            lines.append("Lines: On" if entry.get("show_item_lines") else "Lines: Off")
    if kind == "recipe":
        notes = str(entry.get("body") or "").strip()
        instructions = str(entry.get("instructions") or "").strip()
        if notes:
            lines.append("Notes")
            lines.append(notes[:8000])
        if instructions:
            lines.append("Instructions")
            lines.append(instructions[:8000])
    else:
        body = str(entry.get("body") or "").strip()
        if body and kind != "shopping" and kind != "checklist" and kind != "todo":
            lines.append(body[:8000])
    items = entry.get("items") or []
    if isinstance(items, list) and any(isinstance(row, dict) for row in items):
        lines.append("Items")
        lines.extend(_describe_items([row for row in items if isinstance(row, dict)], grocery=kind == "shopping"))
    ingredients = entry.get("ingredients") or []
    if isinstance(ingredients, list) and any(isinstance(row, dict) for row in ingredients):
        lines.append("Ingredients")
        lines.extend(_describe_ingredients([row for row in ingredients if isinstance(row, dict)]))
    steps = entry.get("steps") or []
    if isinstance(steps, list) and any(isinstance(row, dict) for row in steps):
        lines.append("Steps")
        number = 1
        for step in steps[:100]:
            if not isinstance(step, dict):
                continue
            text = str(step.get("text") or step.get("body") or "")
            step_id = str(step.get("id") or "").strip()
            suffix = f" ({step_id})" if step_id else ""
            lines.append(f"{number}. {text}{suffix}")
            number += 1
        if len(steps) > 100:
            lines.append("Some steps were left out.")
    return "\n".join(lines).strip()
