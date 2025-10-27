# Discord Role Rotation Bot

This is a simple Python bot for Discord that automatically manages a "duty role" (e.g., "On-Call Developer," "Member of the Week") and rotates it among a list of users based on a configurable schedule.

It is built using `discord.py` and its app commands framework.

## Features 


* **=TODO=Automatic Role Rotation:** Configure a schedule (days of the week, hour, minute) for the role to automatically pass to the next user.
* **Dynamic User Management:** Add or remove members from the rotation list directly from Discord using commands.
* **Robust Configuration:** All settings are loaded from external `conf.json` and `users.txt` files.
* **Live Reload:** Reload the configuration files without needing to restart the bot.

## Setup & Installation


### 1. Prerequisites

* Python 3.12 or newer
* A Discord Bot Token (create one at the [Discord Developer Portal](https://discord.com/developers/applications))

### 2. Bot Configuration

1.  **Clone Repository:**
    ```bash
    git clone https://github.com/HackUCF/Role-Rotate-Bot
    cd role-rotate-bot
    ```

2.  **Install Dependencies:**
    A `requirements.txt` is included. Install the dependencies using pip:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set Bot Token and Guild ID:**
    Create a file named `.env` in the root of the project directory. Add your bot token to it:
    ```
    DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
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
    The bot will start and create two new files: `conf.json` and `users.txt`. Update them from defaults.

2. **Set Role Hierarchy in Discord:**
    This is **CRITICAL**. In your Discord server's "Settings" > "Roles", **you must drag the bot's role *above* the duty role** it is supposed to manage. If the bot's role is lower, it will not have permission to assign or remove the role.

3. **Reload the Bot's Config:**
    Once your config files are saved and role hierarchy is set, run the `/reload` command in Discord. The bot will load your new settings and be ready to go.

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