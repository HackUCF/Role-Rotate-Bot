# Discord Role Rotation Bot


This is a simple Python bot for Discord that automatically manages rotating a role.

It is built using `discord.py` and builtin discord commands

## Setup & Installation

### Prereqs:
* Python 3.12 or newer
* A Discord Bot Token (create one at the [Discord Developer Portal](https://discord.com/developers/applications))
* guild id (server id) for the server you will run the bot in
* role id for the role that you want to rotate around

### The downloading and running:


```bash
git clone https://github.com/HackUCF/Role-Rotate-Bot
cd role-rotate-bot
pip install -r requirements.txt
```
Then make a `.env` file, and paste this (puting your token in instead)
```
DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
```
Now you can run it with `python3 main.py` which will make other default files: `users.txt` and `conf.json`. Fill these out with the role and guild, and then use `/reload` inside of your server to reload the config.
```
python3 main.py
```

4.  **Configure Bot Intents:**
    In the [Discord Developer Portal](https://discord.com/developers/applications), 
go to your bot's "Bot" tab and enable the **Server Members Intent**. This is **required**
for the bot to find and manage users. When adding the bot to the server, make sure to allow app_commands in
the oauth section

### 3. First-Time Run & Configuration

1.  **Run the Bot:**
    Run the bot for the first time:
    ```bash
    python main.py
    ```

## Available Commands

* `/reload`: Reloads `conf.json` and `users.txt`. Use this after any manual edit.
* `/force_rotate`: Manually advances the role to the next person in the list.
* `/add_member [member]`: Adds a member to the end of the rotation list.
* `/remove_member [member]`: Removes a member from the rotation list.
* `/debug`: Prints the bot's current loaded configuration to the console.

## TODO
* `/insert_member`
* `/info`
* `/move_member`
* `/set_schedule`
* `/debug` print recent lines of console
* `/set_index`
* Add easter egg (plinksauce?)
* Set up proper logging, and standardize how/where errors are handled
* 
* Merge `users.txt` into `conf.json`
* Add permission checks to commands (e.g., admin-only) using `@app_commands.checks.has_permissions()`.
* add dockerfile
