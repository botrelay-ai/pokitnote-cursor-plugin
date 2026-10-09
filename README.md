# Pokit Note Cursor plugin

This is the Cursor plugin for Pokit Note. Pokit Note enables collaboration with Grok Bot from your phone on to-do lists, shopping, notes, recipes and more.

## Sign in

Open Pokit Note in Cursor and click **Authenticate**. A Pokit Note page opens in the browser. Sign in there, then allow access to your notes, lists, and recipes.

That connection is the one Grok Bot uses. It does not use the key saved by the Pokit Note app on your iPhone, and it does not replace that key.

There is no local program to install. Cursor talks to Pokit Note over the internet.

## Notes

Ask Grok Bot to create a note or change one. A note has a title and text.

## Lists

A list is a List, a Checklist, or a Grocery Shopping list. Grok Bot can create one and can change its name, color, icon, completed items, and lines. Completed items can stay crossed off or be hidden. Grok Bot can add items and change an item's name, checked state, note, and the item it sits under.

A Grocery Shopping list groups items by aisle. The aisles are Fresh Produce, Meat and Fish, Pharmacy, Bakery, Flower Shop, Wine & Beer, Breakfast & Cereal, Baking & Spices, Canned Goods & Soup, Pasta, Rice & Sauces, Condiments, International, Snacks & Crackers, Beverages, Dairy & Eggs, Frozen Foods, and Other.

The list type stays as it was when the list was created. Items can sit in named groups, such as This week. Grok Bot uses a group only when you ask for one or the list already has it, and uses aisles on a Grocery Shopping list.

## Recipes

Grok Bot can create a recipe and change it. A recipe has a name, notes, instructions, a color, and an icon. An ingredient has a name, a quantity, a measurement, and can sit in a group and an aisle. Steps are the ordered method.

## Pokit Note address

The default address is Pokit Note's server, `https://pokitnote.com`.

To test on staging, set **Pokit Note address** in the plugin settings to `https://stage.pokitnote.com`. Leave it blank to use the default. Do not add a slash at the end.
