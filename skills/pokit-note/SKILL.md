---
name: pokit-note
description: Use when someone wants to show, create, or edit notes, lists, or recipes in Pokit Note, or wants Grok Bot connected to Pokit Note.
---

# Pokit Note

Grok Bot shows, creates, and edits notes, lists, and recipes with the Pokit Note MCP tools after the person connects.

- If the Pokit Note MCP is not connected, ask them to install the plugin, open Authenticate on the MCP, sign in on Pokit Note in the browser, and choose Allow. Wait until that is finished.
- Do not start a local Python server, and do not call a local sign-in tool. Cursor Authenticate is the connection.
- Do not ask for, copy, or replace the key saved by the Pokit Note app on the iPhone.
- Then show, create, or edit the notes, lists, or recipes they asked for.
- A note has a title and text. The text may already include formatting from the iPhone. When you change it, keep the rest of the text.
- A list is one of List, Checklist, or Grocery Shopping. Choose that type when you create it. The type cannot be changed later. You can change the name, color, icon, whether completed items are crossed off or hidden, and whether lines are on.
- Add items, and change an item's name, checked state, note, and the item it sits under. One level only.
- On a Grocery Shopping list, set each item's aisle so it sits in that aisle group. The aisles are Fresh Produce, Meat and Fish, Pharmacy, Bakery, Flower Shop, Wine & Beer, Breakfast & Cereal, Baking & Spices, Canned Goods & Soup, Pasta, Rice & Sauces, Snacks & Crackers, Beverages, Dairy & Eggs, and Frozen Foods.
- A custom group name on a List or a Grocery Shopping list is kept on the iPhone. Do not invent one here. Use an aisle for grocery items.
- Do not add Flag, Date, Time, or Urgent.
- A recipe has a name, notes, instructions, a color, and an icon. Ingredients have a name, quantity, measurement, and an optional group and aisle. Steps are the ordered method. Change only the parts the person asked for.
- Open a note, list, or recipe when you need an identifier before editing it.
- Use the Pokit Note address from the plugin settings. The MCP lives at that address plus /mcp/. Change the address when they name a different server. The usual staging address is https://stage.pokitnote.com.
