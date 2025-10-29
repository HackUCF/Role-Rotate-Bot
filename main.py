import logging
import os
from optparse import Option

import discord
from discord import app_commands
from discord.ext.commands.parameters import empty

from RoleRotation import RoleRotation

def codeblock(s: str) -> str:
    return (f"```\n"
            f"{s}\n"
            f"```")

# 1. Get the parent logger and set its level
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)

# # 2. Get the http logger AND set its level too
http_logger = logging.getLogger('discord.http')
http_logger.setLevel(logging.DEBUG)

# 3. Create, format, and add the handler ONLY to the PARENT
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter('[%(asctime)s] [%(levelname)s] %(name)s: %(message)s')
)
logger.addHandler(handler)


class MyClient(discord.Client):
    # Suppress error on the User attribute being None since it fills up later
    user: discord.ClientUser

    def __init__(self, *, intents: discord.Intents, guild_id=0):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.d = RoleRotation(self, guild_id)
        self.guild = discord.Object(id=guild_id)

    # This is run only once, unlike on_ready()
    async def setup_hook(self):
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=self.guild)
        await self.d.load_config()
        # self.d.write_config()
        self.d.scheduler.start()
        commands_synced = await self.tree.sync(guild=self.guild)
        print(commands_synced)

# -------- Init some stuff --------- #
description = "See the app_commands example from the discord.py github"
intents = discord.Intents.default()  # I believe it defaults to none
intents.guilds = True
intents.members = True
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
GUILD_ID = int(GUILD_ID)
client = MyClient(intents=intents, guild_id=GUILD_ID)

@client.event
async def on_ready():
    assert client.user is not None
    print(f'Logged in as {client.user} (ID: {client.user.id})')


# -------- Registering commands --------- #
#todo figure out how to only allow server admins to use the command
#todo im pretty sure it has to do with the @client.tree.check decorator but...
async def add(interaction: discord.Interaction, left: int, right: int):
    """Adds two digits together"""
    await interaction.response.send_message(f"Result: { left + right }")


@client.tree.command(name="debug", description="prints debugging info to console")
async def debug(interaction: discord.Interaction):
    rotation_state = None
    msg = ""
    try:
        rotation_state = codeblock(client.d.__str__())

    except IndexError as e:
        msg += 'The index was out of range. Setting it to zero.'
        client.d.set_index(0, force=True)

    if rotation_state is not None:

        msg = rotation_state
    else:

        msg +=  '(You should `/reload` now).'

    print(msg)
    await interaction.response.send_message(msg)

@client.tree.command(name="force_rotate", description="Force bot to rotate the managed_role.")
async def force_rotate(interaction: discord.Interaction):
    if not await client.d.rotate_role():
        await interaction.response.send_message("Error trying to rotate the role.")
    else:
        await interaction.response.send_message("Done")

@client.tree.command(description="Reload the config files")
async def reload(interaction):
    reloaded = await client.d.load_config() # Must pass in case
    message = "Done"
    if issubclass(type(reloaded), Exception):
        message = (f" There was an error reloading:\n"
                   f"```bash\n"
                   f"{reloaded}\n"
                   f"```")
        print("errored while trying to reload")
    await interaction.response.send_message(message)


@client.tree.command()
@app_commands.describe(
    member="The name of the member to add to the rotation",
    i="The index where you want to insert them"
)
async def add_member(interaction: discord.Interaction, member: discord.Member, i: int=-1):
    """Adds a member to the rotation"""
    result = None
    try:
        if i == -1:
            result = await client.d.add_user(member.id)
        else:
            result = await client.d.add_user(member.id, i)
    except Exception as e:
        await interaction.response.send_message(codeblock(e.__str__()))
        return
    await interaction.response.send_message(f"Added {result} to the list.")

#todo only allow one of the bot's commands to be active at a time
@client.tree.command()
@app_commands.describe(
    member="The name of the member to add to the rotation"
)
async def remove_member(interaction: discord.Interaction, member: discord.Member):
    """Removes a member from the rotation"""
    try:
        deleted = client.d.remove_user(member.id)
    except discord.DiscordException as e:
        await interaction.response.send_message(codeblock(e.__str__()))
        return
    except Exception as e:
        print("something went horribly wrong trying to delete a member")
        await interaction.response.send_message(
            "I probably messed something up in the code:\n " + codeblock(e.__str__()))
        return

    if deleted is None:
        await interaction.response.send_message(f"Didn't find {member.name} in the list.")
    else:
        await interaction.response.send_message(f"Removed {deleted.name}.")

@client.tree.command()
@app_commands.describe(
    i="An index for the rotation to be set to."
)

async def set_index(interaction: discord.Interaction, i: int, force: bool=False):
    message = ""
    try:
        client.d.set_index(i, force)
    except Exception as e:
        await interaction.response.send_message(codeblock(e.__str__()))
        return
    if force:
        message += "Dont forget to reload."
    await interaction.response.send_message(f"Set the index to {i.__str__()} {message}")




# -------- Running the bot --------- #
client.run(TOKEN)