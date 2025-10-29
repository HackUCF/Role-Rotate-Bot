import logging
import os
import discord
from discord import app_commands
from RoleRotation import RoleRotation



# 1. Get the parent logger and set its level
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)

# 2. Get the http logger AND set its level too
http_logger = logging.getLogger('discord.http')
http_logger.setLevel(logging.DEBUG)

# 3. Create, format, and add the handler ONLY to the PARENT
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter('[%(asctime)s] [%(levelname)s] %(name)s: %(message)s')
)
logger.addHandler(handler)


#todo make a run configuration that dont register commands

# MY_GUILD = discord.Object(id=1326775993855381637)
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


@client.tree.command(name="add", description="Adds two numbers together.")
@app_commands.describe(
    left="The first number",
    right="The second number"
)
async def add(interaction: discord.Interaction, left: int, right: int):
    """Adds two digits together"""
    await interaction.response.send_message(f"Result: { left + right }")


@client.tree.command(name="debug", description="prints debugging info to console")
async def debug(interaction: discord.Interaction):
    await interaction.response.send_message("Done.")
    print(client.d)

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
    member="The name of the member to add to the rotation"
)
async def add_member(interaction: discord.Interaction, member: discord.Member):
    """Adds a member to the rotation"""
    error = await client.d.add_user(member.id)
    if error is None:
        await interaction.response.send_message(f"Added {member} to the rotation")
    else:
        await interaction.response.send_message(f"Error:\n"
                                                f"`{error}`")

#todo only allow one of the bot's commands to be active at a time
@client.tree.command()
@app_commands.describe(
    member="The name of the member to add to the rotation"
)
async def remove_member(interaction: discord.Interaction, member: discord.Member):
    """Removes a member from the rotation"""
    deleted = client.d.remove_user(member.id)
    if deleted:
        await interaction.response.send_message(f"Removed {member} from the rotation")
    else:
        await interaction.response.send_message(f"Could not find member: {member}")

@client.tree.command()
@app_commands.describe(
    member="The name of the member to move their position in the schedule",
    index="The 0-indexed position they should be in. 0 Is first in rotation"
)

async def insert_member(interaction: discord.Interaction, member: discord.Member, index: int):
    pass


# -------- Running the bot --------- #
client.run(TOKEN)