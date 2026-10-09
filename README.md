# Pokit Note Cursor plugin

This is the Cursor plugin for Pokit Note. Pokit Note enables collaboration with Grok Bot from your phone on to-do lists, shopping, notes, recipes and more.

Pokit Note is currently only available for iPhone. Support for Android coming soon.

## Sign in

Open Pokit Note in Cursor and click **Authenticate**. A Pokit Note page opens in the browser. Sign in there, then allow access to your notes, lists, and recipes.

That connection is the one Grok Bot uses. It does not use the key saved by the Pokit Note app on your iPhone, and it does not replace that key.

There is no local program to install. Cursor talks to Pokit Note over the internet.

## Lists

A list is a List, a Checklist, or a Grocery Shopping list. Grok Bot can create one and can change its name, color, icon, completed items, and lines. Completed items can stay crossed off or be hidden. Grok Bot can add items and change an item's name, checked state, note, and the item it sits under.

A Grocery Shopping list groups items by aisle. The aisles are Fresh Produce, Meat and Fish, Pharmacy, Bakery, Flower Shop, Wine & Beer, Breakfast & Cereal, Baking & Spices, Canned Goods & Soup, Pasta, Rice & Sauces, Condiments, International, Snacks & Crackers, Beverages, Dairy & Eggs, Frozen Foods, and Other.

The list type stays as it was when the list was created. Items can sit in named groups, such as This week. Grok Bot uses a group only when you ask for one or the list already has it, and uses aisles on a Grocery Shopping list.

## Recipes

Grok Bot can create a recipe and change it. A recipe has a name, notes, instructions, a color, and an icon. An ingredient has a name, a quantity, a measurement, and can sit in a group and an aisle. Steps are the ordered method.

## Notes

Ask Grok Bot to create a note or change one. A note has a title and text.

## Connect Your Assistant

Connect Grok Bot to the Pokit Note app so you can share links and photos with it and it hears about your changes.

1. Install the Pokit Note plugin in Grok Bot, click **Authenticate**, sign in to Pokit Note, and allow access.
2. Ask Grok Bot: "Set up a routine that handles my Pokit Note Connected Assistant webhook, following the Pokit Note connected assistant skill." Grok Bot creates a routine that runs when Pokit Note calls its webhook.
3. Open the routine's settings in the Grok Bot sidebar and copy its Webhook URL and Authorization header (the key). Grok Bot links you there. It won't paste the key into chat.
4. In the Pokit Note app on your iPhone, open Account, then Connected Assistant, and choose Grok Bot. Paste the URL and the key, tap Save, then tap Send Test. Grok Bot confirms it got the test.

After that:

- Share links and photos from the iPhone share sheet with a prompt, as shown below.
- Grok Bot gets a notice when you change a list, note, or recipe. Turn notices off for one item in its Info, or for everything in Connected Assistant settings.

## Share photos and web pages with Grok Bot

In Safari, Photos, or any app, tap Share, choose Pokit Note, pick a quick prompt or type your own, and tap Send. Grok Bot handles it and tells you what it did.

- Recipe page: "Get the recipe from this page and add it to my recipes." Grok Bot saves it to Recipes with the ingredients sorted into grocery aisles, plus the steps.
- Article: "Summarize this page and create a note." You get a new note with a short summary and the link.
- Product page: "Add the item on this page to my shopping list." It goes on your grocery list in the right aisle.
- Photo of a dish: "Find the best recipe for this dish and add it to my recipes."
- Photo of something you're out of: "Identify this and add it to my shopping list."

Shared photos are stored privately and deleted after 7 days.

## Turn a recipe into a shopping list
Ask Grok Bot in plain words:

- "Add the ingredients for Chicken Marsala to my Shopping list."
- "Add everything for Stuffed Bell Peppers to my grocery list except the rice."
- "I'm making Banana Bread and Chicken Marsala this weekend. Put what I need on my Shopping list."

Ingredients land in the right aisle with their amounts, like "Flour (2 cup)". Anything already on the list and not checked off is skipped, so adding the same recipe twice doesn't create duplicates. Grok Bot tells you what it added and what it skipped.
