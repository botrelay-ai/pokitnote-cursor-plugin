#!/usr/bin/env python3
"""Pokit Note tools for Grok Bot. Speaks the plugin tool protocol on standard input."""

from __future__ import annotations

import json
import sys

from connection import (
    ConnectionError,
    api_base,
    clear_connection,
    current_connection,
    describe_entry,
    list_kind,
    load_connection,
    open_entry,
    revoke_connection,
    save_connection,
    summarize_entries,
    wait_for_sign_in,
)

TOOLS = [
    {
        "name": "sign_in",
        "title": "Sign in to Pokit Note",
        "description": "Open Pokit Note so you can sign in and allow Grok Bot to use your notes, lists, and recipes.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sign_out",
        "title": "Disconnect Pokit Note",
        "description": "Stop Grok Bot from using your Pokit Note account.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_notes",
        "title": "Show notes",
        "description": "Show the notes in Pokit Note.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_lists",
        "title": "Show lists",
        "description": "Show the lists in Pokit Note.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_recipes",
        "title": "Show recipes",
        "description": "Show the recipes in Pokit Note.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "open_item",
        "title": "Open a note, list, or recipe",
        "description": "Open one note, list, or recipe from Pokit Note.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "The identifier shown next to the note, list, or recipe.",
                }
            },
            "required": ["id"],
        },
    },
]


def read_message():
    line = sys.stdin.buffer.readline()
    if not line:
        return None
    if line.lstrip().startswith(b"{"):
        return json.loads(line.decode("utf-8"))
    headers = [line]
    while True:
        extra = sys.stdin.buffer.readline()
        if not extra or extra in (b"\r\n", b"\n"):
            break
        headers.append(extra)
    length = 0
    for header in headers:
        text = header.decode("utf-8", errors="replace")
        if text.lower().startswith("content-length:"):
            length = int(text.split(":", 1)[1].strip())
    if length <= 0:
        return None
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def write_message(payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def notify(text: str) -> None:
    write_message({"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info", "data": text}})


def tool_result(text: str, is_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def handle_tool(name: str, arguments: dict) -> dict:
    base = api_base()
    try:
        if name == "sign_in":
            _sign_in(base)
            return tool_result("Grok Bot is connected to Pokit Note and can read your notes, lists, and recipes.")
        if name == "sign_out":
            connection = load_connection()
            if connection is None:
                return tool_result("Grok Bot is not connected to Pokit Note.")
            try:
                revoke_connection(base, connection)
            except ConnectionError:
                clear_connection()
                return tool_result(
                    "Grok Bot is no longer connected on this computer. Pokit Note could not be reached to finish disconnecting."
                )
            clear_connection()
            return tool_result("Grok Bot is no longer connected to Pokit Note. The iPhone app was left as it is.")
        if name == "list_notes":
            connection = current_connection(base)
            text = summarize_entries(list_kind(base, connection, "note"), "No notes yet.")
            return tool_result(text)
        if name == "list_lists":
            connection = current_connection(base)
            lists = list_kind(base, connection, "checklist") + list_kind(base, connection, "shopping")
            return tool_result(summarize_entries(lists, "No lists yet."))
        if name == "list_recipes":
            connection = current_connection(base)
            return tool_result(summarize_entries(list_kind(base, connection, "recipe"), "No recipes yet."))
        if name == "open_item":
            connection = current_connection(base)
            entry = open_entry(base, connection, str(arguments.get("id") or ""))
            return tool_result(describe_entry(entry))
    except ConnectionError as exc:
        return tool_result(str(exc), is_error=True)
    return tool_result("That action is not available.", is_error=True)


def _sign_in(base: str) -> None:
    def announce(url: str) -> None:
        notify(
            "Sign in on this Pokit Note page, then allow access to your notes, lists, and recipes.\n" + url
        )

    _url, connection = wait_for_sign_in(base, on_url=announce)
    save_connection(connection)


def handle(message: dict) -> dict | None:
    method = message.get("method")
    message_id = message.get("id")
    if method == "notifications/initialized" or message_id is None and method != "initialize":
        if message_id is None:
            return None
    if method == "initialize":
        version = (message.get("params") or {}).get("protocolVersion") or "2024-11-05"
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "Pokit Note", "version": "0.1.0"},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": message_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params") or {}
        result = handle_tool(str(params.get("name") or ""), params.get("arguments") or {})
        return {"jsonrpc": "2.0", "id": message_id, "result": result}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": message_id, "result": {}}
    if message_id is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": -32601, "message": "That action is not available."},
    }


def main() -> None:
    while True:
        message = read_message()
        if message is None:
            return
        if not isinstance(message, dict):
            continue
        response = handle(message)
        if response is not None:
            write_message(response)


if __name__ == "__main__":
    main()
