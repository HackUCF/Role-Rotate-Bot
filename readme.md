# Discord Role Rotation Bot


This is a simple Python bot for Discord that automatically manages rotating a role.

It is built using `discord.py` and builtin discord commands

## Setup & Installation

### Prereqs:
* Python 3.12 or newer
* A Discord Bot Token (create one at the [Discord Developer Portal](https://discord.com/developers/applications))

### The downloading and running:


```bash
git clone https://github.com/HackUCF/Role-Rotate-Bot
cd role-rotate-bot
pip install -r requirements.txt
```
Then make a `.env` file fill it out like this:
```
DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
```
Now you can run it with `python3 main.py` which will make other default files: `users.txt` and `conf.json`. Fill these out and use `/reload` inside of your server to reload the config.
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
* implement per member scheduling?
  * someone is never avaible on mondays, so remove them
  * rather than rotating when that happens, setup substitututions: `0 jmoney 1:jstyles` 
    * every monday that jmoney has, jstyles will be pinged and told he is on duty instead
  * substitutions could also be ephemeral, so specify a date to be unavailble and the scheduler will overide rotations with whatever it has logged
* actually implement the scheduler lol
  * somethinng to set the next rotate time/date
  * something to watch the time and update when it hits that point
* Implement the `/insert_member` command to add a user at a specific index.
* Add permission checks to commands (e.g., admin-only) using `@app_commands.checks.has_permissions()`.
