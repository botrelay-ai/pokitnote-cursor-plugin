# Pokit Note Cursor plugin

This is the Cursor plugin for Pokit Note. Grok Bot can show, create, and edit your notes, lists, and recipes.

## Connect

1. Install the plugin.
2. Open Authenticate on the Pokit Note MCP.
3. Sign in on Pokit Note in the browser.
4. Choose Allow.

Cursor keeps that connection. The plugin talks to Pokit Note over remote HTTP. It does not start a local Python server, it does not use the key saved by the Pokit Note app on your iPhone, and it does not replace that key.

Authenticate works after staging is deployed with the Pokit Note Streamable HTTP MCP. Until that deploy, the plugin can be installed, and the sign-in page will not finish.

## Notes

Ask Grok Bot to create a note or change one. A note has a title and text.

## Lists

A list is a List, a Checklist, or a Grocery Shopping list. Grok Bot can create one and can change its name, color, icon, completed items, and lines. Completed items can stay crossed off or be hidden. Grok Bot can add items and change an item's name, checked state, note, and the item it sits under.

A Grocery Shopping list groups items by aisle. The aisles are Fresh Produce, Meat and Fish, Pharmacy, Bakery, Flower Shop, Wine & Beer, Breakfast & Cereal, Baking & Spices, Canned Goods & Soup, Pasta, Rice & Sauces, Snacks & Crackers, Beverages, Dairy & Eggs, and Frozen Foods.

The list type stays as it was when the list was created. A custom group name on a List or a Grocery Shopping list is kept on the iPhone and is not saved from here.

## Recipes

Grok Bot can create a recipe and change it. A recipe has a name, notes, instructions, a color, and an icon. An ingredient has a name, a quantity, a measurement, and can sit in a group and an aisle. Steps are the ordered method.

## Pokit Note address

The usual address is the staging server, `https://stage.pokitnote.com`. The MCP address is that server plus `/mcp/`, for example `https://stage.pokitnote.com/mcp/`.

You can switch it. In the plugin settings, set **Pokit Note address** to the server where your account lives. Do not add a trailing slash. Leave it blank to keep using staging.
