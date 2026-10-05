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
    if status == 401:
        return "Sign in to Pokit Note again."
    return "Pokit Note could not complete that request."


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


def api_get(base: str, connection: Connection, path: str) -> dict:
    request = urllib.request.Request(
        f"{base}{path}",
        method="GET",
        headers={"Authorization": f"Bearer {connection.access_token}", "Accept": "application/json"},
    )
    try:
        return _read_json(request)
    except ConnectionError as exc:
        if getattr(exc, "status", None) != 401:
            raise
        refreshed = refresh_connection(base, connection)
        save_connection(refreshed)
        request = urllib.request.Request(
            f"{base}{path}",
            method="GET",
            headers={"Authorization": f"Bearer {refreshed.access_token}", "Accept": "application/json"},
        )
        return _read_json(request)


def list_kind(base: str, connection: Connection, kind: str) -> list[dict]:
    body = api_get(base, connection, f"/api/entries?kind={urllib.parse.quote(kind)}")
    entries = body.get("entries")
    if not isinstance(entries, list):
        raise ConnectionError("Pokit Note did not return your items.")
    return [item for item in entries if isinstance(item, dict)]


def open_entry(base: str, connection: Connection, entry_id: str) -> dict:
    cleaned = entry_id.strip()
    if not cleaned:
        raise ConnectionError("Choose a note, list, or recipe first.")
    body = api_get(base, connection, f"/api/entries/{urllib.parse.quote(cleaned)}")
    return body


def summarize_entries(entries: list[dict], empty: str) -> str:
    if not entries:
        return empty
    lines = []
    for entry in entries[:100]:
        title = str(entry.get("title") or "Untitled").replace("\n", " ")
        identifier = str(entry.get("id") or "")
        lines.append(f"- {title} ({identifier})" if identifier else f"- {title}")
    if len(entries) > 100:
        lines.append("Some items were left out.")
    return "\n".join(lines)


def describe_entry(entry: dict) -> str:
    title = str(entry.get("title") or "Untitled")
    kind = str(entry.get("kind") or "")
    labels = {"note": "Note", "checklist": "List", "shopping": "List", "recipe": "Recipe"}
    lines = [f"{labels.get(kind, 'Item')}: {title}"]
    body = str(entry.get("body") or "").strip()
    if body:
        lines.append(body[:8000])
    for label, key in (("Items", "items"), ("Ingredients", "ingredients")):
        rows = entry.get(key) or []
        if isinstance(rows, list) and rows:
            lines.append(label)
            for row in rows[:100]:
                if isinstance(row, dict):
                    lines.append(f"- {row.get('text') or row.get('name') or 'Untitled'}")
    steps = entry.get("steps") or []
    if isinstance(steps, list) and steps:
        lines.append("Steps")
        for index, step in enumerate(steps[:100], start=1):
            if isinstance(step, dict):
                lines.append(f"{index}. {step.get('text') or step.get('body') or ''}")
    return "\n".join(lines).strip()
