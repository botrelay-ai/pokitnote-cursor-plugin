<h1>
<img src="assets/logo.png" alt="Pokit Note" width="64" style="vertical-align: middle;"/>&nbsp; &nbsp; Pokit Note Cursor Plugin
</h1>

This is the Cursor plugin for Pokit Note (pronounced 'Pocket Note'). Pokit Note enables collaboration with Grok Bot from your phone on to-do lists, shopping, notes, recipes and more.

Pokit Note is currently only available for iPhone, and only in the US. Android support coming soon.

## Install and Connect Grok Bot

Install the plugin through Cursor and connect Grok Bot to the Pokit Note app on your iPhone to share links and photos with agents and collaborate on updates.

1. **Install the Plugin** in Cursor.
   - **Now:** Open Settings > Open Customize > Marketplace. Click **Add Marketplace**, choose **Import from GitHub**, and enter https://github.com/botrelay-ai/pokitnote-cursor-plugin. Find the Pokit Note plugin and click the Add button to install it.
   - **Once Pokit Note is listed in the Marketplace:** Open Settings > Open Customize > Marketplace, search for "Pokit Note", and click Add to install it.
2. After the Pokit Note plugin is added, open it to access the configuration. Under MCPs, next to Pokit Note, click **Authenticate**. This will open the Pokit Note website in the default browser. If you don't already have an account, create one, and then sign in and choose **Approve** to complete the setup.
3. With the plugin authenticated and authorized, prompt your Grok Bot agent with the following: "Set up a routine that handles my Pokit Note Connected Assistant webhook, following the Pokit Note connected assistant skill." Grok Bot creates a routine that runs when Pokit Note calls its webhook.
4. Open the routine's settings in the Grok Bot sidebar and copy its Webhook URL and Webhook Key. **Note:** you may have to ask the agent for a link to the routine in order to access the Webhook URL and Webhook Key.
5. In the Pokit Note app on your iPhone, open Account, then Connected Assistant, and choose Grok Bot. Paste the URL and the key, tap Save, then tap Send Test. Grok Bot confirms it got the test.

## Address

Leave Pokit Note address unset for normal use. The connector uses https://pokitnote.com/mcp with no trailing slash.

That field is an optional override of the MCP URL. Set it only when you are pointing the connector at a different Pokit Note server, and omit any trailing slash.

## Subscription

Assistant setup and Send Test work right away. Every new account gets 7 days of full access. After that, editing, sharing, and change notices need the free trial (free for the first month) or a subscription ($29.99/year through the App Store). Without one, the account is read-only.

## Lists

A list is a List, a Checklist, or a Grocery Shopping list. Grok Bot can create one and can change its name, color, icon, completed items, and lines. Completed items can stay crossed off or be hidden. Grok Bot can add items and change an item's name, checked state, note, flag, due date, urgent alarm, and the item it sits under. A flag marks an item as important. A due date is a day, or a day and a time. An urgent alarm rings on your phones at that time, and it needs a due date with a time.

A Grocery Shopping list groups items by aisle. The aisles are Fresh Produce, Meat and Fish, Pharmacy, Bakery, Flower Shop, Wine & Beer, Breakfast & Cereal, Baking & Spices, Canned Goods & Soup, Pasta, Rice & Sauces, Condiments, International, Snacks & Crackers, Beverages, Coffee & Tea, Dairy & Eggs, Frozen Foods, Pet Food, and Other. Coffee beans, ground coffee, K-cups, and tea go in Coffee & Tea, not Beverages. Dog and cat food, treats, and litter go in Pet Food.

The list type stays as it was when the list was created. Items can sit in named groups, such as This week. Grok Bot uses a group only when you ask for one or the list already has it, and uses aisles on a Grocery Shopping list.

Checked items you clear from a Grocery Shopping list stay under Recently Bought for 90 days. Grok Bot can put one back on a list.

Grok Bot can catch up on recent changes to your notes, lists, and recipes.

## Recipes

Grok Bot can create a recipe and change it. A recipe has a name, notes, instructions, a color, and an icon. An ingredient has a name, a quantity, a measurement, and can sit in a group and an aisle. Ingredients can be checked off, and Grok Bot can add a recipe's ingredients to a grocery list in one step. Steps are the ordered method.

## Notes

Ask Grok Bot to create a note or change one. A note has a title and text.

## How to Collaborate With Grok Bot

- Share links and photos from the iPhone share sheet with a prompt, as shown below.
- Grok Bot gets a notice when you change a list, note, or recipe. Turn notices off for one item in its Info, or for everything in Connected Assistant settings.

In Safari, Photos, or any app, tap Share, choose Pokit Note, pick a quick prompt or type your own, and tap Send. Grok Bot handles it and tells you what it did.

- Recipe page: "Get the recipe from this page and add it to my recipes." Grok Bot saves it to Recipes with the ingredients sorted into grocery aisles, plus the steps.
- Article: "Summarize this page and create a note." You get a new note with a short summary and the link.
- Product page: "Add the item on this page to my shopping list." It goes on your grocery list in the right aisle.
- Photo of a dish: "Find the best recipe for this dish and add it to my recipes."
- Photo of something you're out of: "Identify this and add it to my shopping list."

Shared photos are stored privately and deleted after 7 days.

## Turn a Recipe Into a Shopping List

Ask Grok Bot in plain words:

- "Add the ingredients for Chicken Marsala to my Shopping list."
- "Add everything for Stuffed Bell Peppers to my grocery list except the rice."
- "I'm making Banana Bread and Chicken Marsala this weekend. Put what I need on my Shopping list."

Ingredients land in the right aisle with their amounts, like "Flour (2 cup)". Anything already on the list and not checked off is skipped, so adding the same recipe twice doesn't create duplicates. Grok Bot tells you what it added and what it skipped.

## Links

- Connect Grok Bot guide: https://pokitnote.com/connect/grok-bot
- Support: https://pokitnote.com/support
- Privacy: https://pokitnote.com/privacy
- Terms: https://pokitnote.com/terms
