#!/usr/bin/env python3
"""Pokit Note tools for Grok Bot. Speaks the plugin tool protocol on standard input."""

from __future__ import annotations

import json
import sys

from connection import (
    AISLES,
    ConnectionError,
    ICONS,
    add_ingredient,
    add_list_item,
    add_step,
    api_base,
    clear_connection,
    create_list,
    create_note,
    create_recipe,
    current_connection,
    describe_entry,
    edit_ingredient,
    edit_list,
    edit_list_item,
    edit_note,
    edit_recipe,
    edit_step,
    list_kind,
    list_lists,
    load_connection,
    open_entry,
    revoke_connection,
    save_connection,
    summarize_entries,
    wait_for_sign_in,
)

COLORS = ["Sky blue", "Deep blue", "Green", "Orange", "Red", "Purple"]
COMPLETED = ["Cross Off", "Hide"]
LIST_TYPE_NAMES = ["List", "Checklist", "Grocery Shopping"]

_COLOR = {"type": "string", "enum": COLORS, "description": "A Pokit Note color."}
_ICON = {"type": "string", "enum": list(ICONS), "description": "An icon Pokit Note uses."}
_AISLE = {
    "type": "string",
    "enum": ["", *AISLES],
    "description": "A grocery aisle. Use an empty string when there is no aisle.",
}
_COMPLETED = {
    "type": "string",
    "enum": COMPLETED,
    "description": "What happens to a checked item. Cross Off keeps it visible. Hide takes it off the list.",
}
_LINES = {"type": "boolean", "description": "True to show lines between items."}
_INGREDIENT = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "The ingredient name."},
        "quantity": {"type": "string", "description": "How much, such as 1 or 1/2."},
        "measurement": {"type": "string", "description": "The measurement, such as cup or teaspoon."},
        "group": {"type": "string", "description": "The ingredient group, such as Sauce. Leave it blank when there is no group."},
        "aisle": _AISLE,
    },
    "required": ["name"],
}

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
        "description": "Show the lists in Pokit Note. A list is a List, a Checklist, or a Grocery Shopping list.",
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
    {
        "name": "create_note",
        "title": "Create a note",
        "description": "Create a note with a title and text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The note title."},
                "text": {"type": "string", "description": "The note text."},
            },
            "required": ["title"],
        },
    },
    {
        "name": "edit_note",
        "title": "Edit a note",
        "description": "Change a note's title or text. Only the parts you include are changed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "The identifier shown next to the note."},
                "title": {"type": "string", "description": "The new title."},
                "text": {"type": "string", "description": "The new text. Use an empty string to clear it."},
            },
            "required": ["id"],
        },
    },
    {
        "name": "create_list",
        "title": "Create a list",
        "description": "Create a List, Checklist, or Grocery Shopping list. The type cannot be changed later.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The list name."},
                "type": {
                    "type": "string",
                    "enum": LIST_TYPE_NAMES,
                    "description": "List, Checklist, or Grocery Shopping.",
                },
                "color": _COLOR,
                "icon": _ICON,
                "completed": _COMPLETED,
                "lines": _LINES,
            },
            "required": ["title", "type"],
        },
    },
    {
        "name": "edit_list",
        "title": "Edit a list",
        "description": "Change a list's name, color, icon, completed items, or lines. The list type stays as it is. Only the parts you include are changed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "The identifier shown next to the list."},
                "title": {"type": "string", "description": "The new name."},
                "color": _COLOR,
                "icon": _ICON,
                "completed": _COMPLETED,
                "lines": _LINES,
            },
            "required": ["id"],
        },
    },
    {
        "name": "add_list_item",
        "title": "Add a list item",
        "description": "Add an item to a list. On a Grocery Shopping list, set the aisle so the item sits in that aisle group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "list_id": {"type": "string", "description": "The identifier shown next to the list."},
                "text": {"type": "string", "description": "The item name."},
                "aisle": _AISLE,
                "under": {
                    "type": "string",
                    "description": "The identifier of the item this one sits under. One level only.",
                },
            },
            "required": ["list_id", "text"],
        },
    },
    {
        "name": "edit_list_item",
        "title": "Edit a list item",
        "description": "Change an item's name, checked state, note, aisle, or the item it sits under. Only the parts you include are changed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "list_id": {"type": "string", "description": "The identifier shown next to the list."},
                "item_id": {"type": "string", "description": "The identifier shown next to the item."},
                "text": {"type": "string", "description": "The new item name."},
                "checked": {"type": "boolean", "description": "True when the item is checked off."},
                "note": {"type": "string", "description": "A note under the item. Use an empty string to clear it."},
                "aisle": _AISLE,
                "under": {
                    "type": "string",
                    "description": "The identifier of the item this one sits under. One level only. Use an empty string to put it on its own.",
                },
            },
            "required": ["list_id", "item_id"],
        },
    },
    {
        "name": "create_recipe",
        "title": "Create a recipe",
        "description": "Create a recipe with a name, notes, instructions, ingredients, and steps. An ingredient has a name, quantity, measurement, and an optional group and aisle. Recipes usually use fork.knife, birthday.cake, wineglass, carrot, fish, leaf, flame, basket, or cart.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The recipe name."},
                "notes": {"type": "string", "description": "Notes about the recipe."},
                "instructions": {"type": "string", "description": "The written method."},
                "color": _COLOR,
                "icon": _ICON,
                "ingredients": {"type": "array", "items": _INGREDIENT, "description": "The ingredients, including their groups."},
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The steps, in order.",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "edit_recipe",
        "title": "Edit a recipe",
        "description": "Change a recipe's name, notes, instructions, color, or icon. Only the parts you include are changed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "The identifier shown next to the recipe."},
                "title": {"type": "string", "description": "The new name."},
                "notes": {"type": "string", "description": "The new notes. Use an empty string to clear them."},
                "instructions": {"type": "string", "description": "The new instructions. Use an empty string to clear them."},
                "color": _COLOR,
                "icon": _ICON,
            },
            "required": ["id"],
        },
    },
    {
        "name": "add_ingredient",
        "title": "Add an ingredient",
        "description": "Add an ingredient to a recipe. Include the group, quantity, and measurement when the recipe has them.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_id": {"type": "string", "description": "The identifier shown next to the recipe."},
                "name": {"type": "string", "description": "The ingredient name."},
                "quantity": {"type": "string", "description": "How much, such as 1 or 1/2."},
                "measurement": {"type": "string", "description": "The measurement, such as cup or teaspoon."},
                "group": {"type": "string", "description": "The ingredient group, such as Sauce."},
                "aisle": _AISLE,
            },
            "required": ["recipe_id", "name"],
        },
    },
    {
        "name": "edit_ingredient",
        "title": "Edit an ingredient",
        "description": "Change an ingredient's name, quantity, measurement, group, aisle, or checked state. Only the parts you include are changed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_id": {"type": "string", "description": "The identifier shown next to the recipe."},
                "ingredient_id": {"type": "string", "description": "The identifier shown next to the ingredient."},
                "name": {"type": "string", "description": "The new ingredient name."},
                "quantity": {"type": "string", "description": "The new quantity. Use an empty string to clear it."},
                "measurement": {"type": "string", "description": "The new measurement. Use an empty string to clear it."},
                "group": {"type": "string", "description": "The ingredient group. Use an empty string to remove the group."},
                "aisle": _AISLE,
                "checked": {"type": "boolean", "description": "True when the ingredient is checked off."},
            },
            "required": ["recipe_id", "ingredient_id"],
        },
    },
    {
        "name": "add_step",
        "title": "Add a step",
        "description": "Add a step to a recipe.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_id": {"type": "string", "description": "The identifier shown next to the recipe."},
                "text": {"type": "string", "description": "The step."},
            },
            "required": ["recipe_id", "text"],
        },
    },
    {
        "name": "edit_step",
        "title": "Edit a step",
        "description": "Change the text of a recipe step.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_id": {"type": "string", "description": "The identifier shown next to the recipe."},
                "step_id": {"type": "string", "description": "The identifier shown next to the step."},
                "text": {"type": "string", "description": "The new step."},
            },
            "required": ["recipe_id", "step_id", "text"],
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


def _required_text(arguments: dict, key: str, missing: str) -> str:
    if key not in arguments or arguments[key] is None:
        raise ConnectionError(missing)
    value = arguments[key]
    if not isinstance(value, str):
        raise ConnectionError("That needs to be text.")
    return value


def _optional_text(arguments: dict, key: str) -> str | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ConnectionError("That needs to be text.")
    return value


def _optional_bool(arguments: dict, key: str) -> bool | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, bool):
        raise ConnectionError("That needs to be yes or no.")
    return value


def _optional_rows(arguments: dict, key: str, message: str) -> list | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, list):
        raise ConnectionError(message)
    return value


def handle_tool(name: str, arguments: dict) -> dict:
    base = api_base()
    try:
        if name == "sign_in":
            _sign_in(base)
            return tool_result("Grok Bot is connected to Pokit Note and can use your notes, lists, and recipes.")
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
            return tool_result(summarize_entries(list_lists(base, connection), "No lists yet."))
        if name == "list_recipes":
            connection = current_connection(base)
            return tool_result(summarize_entries(list_kind(base, connection, "recipe"), "No recipes yet."))
        if name == "open_item":
            connection = current_connection(base)
            entry = open_entry(base, connection, str(arguments.get("id") or ""))
            return tool_result(describe_entry(entry))
        if name == "create_note":
            connection = current_connection(base)
            entry = create_note(
                base,
                connection,
                _required_text(arguments, "title", "Enter a name."),
                _optional_text(arguments, "text") or "",
            )
            return tool_result(describe_entry(entry))
        if name == "edit_note":
            connection = current_connection(base)
            entry = edit_note(
                base,
                connection,
                _required_text(arguments, "id", "Choose a note first."),
                title=_optional_text(arguments, "title"),
                body=_optional_text(arguments, "text"),
            )
            return tool_result(describe_entry(entry))
        if name == "create_list":
            connection = current_connection(base)
            entry = create_list(
                base,
                connection,
                _required_text(arguments, "title", "Enter a name."),
                _required_text(arguments, "type", "Pick List, Checklist, or Grocery Shopping."),
                color=_optional_text(arguments, "color"),
                icon=_optional_text(arguments, "icon"),
                completed=_optional_text(arguments, "completed"),
                lines=_optional_bool(arguments, "lines"),
            )
            return tool_result(describe_entry(entry))
        if name == "edit_list":
            connection = current_connection(base)
            entry = edit_list(
                base,
                connection,
                _required_text(arguments, "id", "Choose a list first."),
                title=_optional_text(arguments, "title"),
                color=_optional_text(arguments, "color"),
                icon=_optional_text(arguments, "icon"),
                completed=_optional_text(arguments, "completed"),
                lines=_optional_bool(arguments, "lines"),
            )
            return tool_result(describe_entry(entry))
        if name == "add_list_item":
            connection = current_connection(base)
            entry = add_list_item(
                base,
                connection,
                _required_text(arguments, "list_id", "Choose a list first."),
                _required_text(arguments, "text", "Enter an item."),
                aisle=_optional_text(arguments, "aisle"),
                under=_optional_text(arguments, "under"),
            )
            return tool_result(describe_entry(entry))
        if name == "edit_list_item":
            connection = current_connection(base)
            entry = edit_list_item(
                base,
                connection,
                _required_text(arguments, "list_id", "Choose a list first."),
                _required_text(arguments, "item_id", "Choose an item first."),
                text=_optional_text(arguments, "text"),
                checked=_optional_bool(arguments, "checked"),
                note=_optional_text(arguments, "note"),
                aisle=_optional_text(arguments, "aisle"),
                under=_optional_text(arguments, "under"),
            )
            return tool_result(describe_entry(entry))
        if name == "create_recipe":
            connection = current_connection(base)
            entry = create_recipe(
                base,
                connection,
                _required_text(arguments, "title", "Enter a name."),
                notes=_optional_text(arguments, "notes"),
                instructions=_optional_text(arguments, "instructions"),
                color=_optional_text(arguments, "color"),
                icon=_optional_text(arguments, "icon"),
                ingredients=_optional_rows(arguments, "ingredients", "Ingredients need to be a list."),
                steps=_optional_rows(arguments, "steps", "Steps need to be a list."),
            )
            return tool_result(describe_entry(entry))
        if name == "edit_recipe":
            connection = current_connection(base)
            entry = edit_recipe(
                base,
                connection,
                _required_text(arguments, "id", "Choose a recipe first."),
                title=_optional_text(arguments, "title"),
                notes=_optional_text(arguments, "notes"),
                instructions=_optional_text(arguments, "instructions"),
                color=_optional_text(arguments, "color"),
                icon=_optional_text(arguments, "icon"),
            )
            return tool_result(describe_entry(entry))
        if name == "add_ingredient":
            connection = current_connection(base)
            entry = add_ingredient(
                base,
                connection,
                _required_text(arguments, "recipe_id", "Choose a recipe first."),
                _required_text(arguments, "name", "Enter an ingredient."),
                quantity=_optional_text(arguments, "quantity") or "",
                measurement=_optional_text(arguments, "measurement") or "",
                group=_optional_text(arguments, "group") or "",
                aisle=_optional_text(arguments, "aisle") or "",
            )
            return tool_result(describe_entry(entry))
        if name == "edit_ingredient":
            connection = current_connection(base)
            entry = edit_ingredient(
                base,
                connection,
                _required_text(arguments, "recipe_id", "Choose a recipe first."),
                _required_text(arguments, "ingredient_id", "Choose an ingredient first."),
                name=_optional_text(arguments, "name"),
                quantity=_optional_text(arguments, "quantity"),
                measurement=_optional_text(arguments, "measurement"),
                group=_optional_text(arguments, "group"),
                aisle=_optional_text(arguments, "aisle"),
                checked=_optional_bool(arguments, "checked"),
            )
            return tool_result(describe_entry(entry))
        if name == "add_step":
            connection = current_connection(base)
            entry = add_step(
                base,
                connection,
                _required_text(arguments, "recipe_id", "Choose a recipe first."),
                _required_text(arguments, "text", "Enter a step."),
            )
            return tool_result(describe_entry(entry))
        if name == "edit_step":
            connection = current_connection(base)
            entry = edit_step(
                base,
                connection,
                _required_text(arguments, "recipe_id", "Choose a recipe first."),
                _required_text(arguments, "step_id", "Choose a step first."),
                _required_text(arguments, "text", "Enter a step."),
            )
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
                "serverInfo": {"name": "Pokit Note", "version": "0.2.0"},
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
