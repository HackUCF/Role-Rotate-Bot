import json

from enum import Enum
from pathlib import (Path)
from random import random
import re
from typing import override, List, Optional, Union

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import functools
import asyncio

#todo unhandled error when you try to do stuff with people who just left the server discord.app_commands.errors.TransformerError
class Days(int, Enum):
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6


class ConfKeys(str, Enum):
    ROLE_ID = "role_id"
    SCHEDULE_DAY = "schedule_day"
    SCHEDULE_HOUR = "schedule_hour"
    SCHEDULE_MINUTE = "schedule_minute"
    INDEX = "index"

USERS_FILE_NAME = Path("./users.txt")
CONFIG_FILE_NAME = Path("./conf.json")

def config_required(func):
    """
    A decorator that stops a method from running if self.config_good is False.
    Handles both synchronous and asynchronous methods.
    """

    @functools.wraps(func)
    async def async_wrapper(self, *args, **kwargs):
        # The 'self' argument is the instance of RoleRotation
        if not self.config_good:
            print(f"Cannot run '{func.__name__}': Config is not loaded. Please run load_config().")
            return
        return await func(self, *args, **kwargs)

    @functools.wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        # The 'self' argument is the instance of RoleRotation
        if not self.config_good:
            print(f"Cannot run '{func.__name__}': Config is not loaded. Please run load_config().")
            return
        return func(self, *args, **kwargs)

    # Return the correct wrapper based on whether the original function was async
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# Manages the list of member_ids to rotate into duty, and the configuration for the app
# You MUST await load_config before using this class
class RoleRotation:
    """
    Manages the rotation of a Discord role among a list of members.

    Usage:
    1. Create an instance: `rotation_manager = RoleRotation()`
    2. Load the configuration: `await rotation_manager.load_config(client)`
    3. Check if loading was successful: `if rotation_manager.config_good:`
    4. Call methods like `rotate_role()`

    To reload,
    simply call `await rotation_manager.load_config(client)` again.
    """

    def __init__(self, client: discord.Client, guild_id: int):
        """Initializes the RoleRotation object in an unconfigured state."""

        # Note that because we are not loggged in when this class is typically instanstanciated,
        # most values have to be 0 or None until we are able to fetch the data with async operations
        # additionally reading config from disk might fail, but we never want the class to fail to init
        # Hence why loading must be explictly called using load_config

        # --- Config State ---
        self.config_good: bool = False
        self.scheduler = AsyncIOScheduler()
        self.guild_id: int = guild_id
        self.client = client


        # --- Fetched Discord Objects ---
        self.managed_role: Optional[discord.Role] = None
        self.members: List[discord.Member] = []
        self.guild: discord.Guild = None

        # --- Config File Values ---
        self.member_ids: List[int] = []
        self.role_id: Optional[int] = None
        self.index: int = 0
        self.schedule_day: int = 0
        self.schedule_hour: int = 0
        self.schedule_minute: int = 0


    async def load_config(self) -> Optional[Exception]:
        """
        Loads configuration from disk and fetches required Discord objects.
        This method fully populates the object's state.

        Returns True on success, False on failure.
        """
        # We only want to load the guild once:
        if self.guild is None:
            self.guild = await self.client.fetch_guild(self.guild_id)

        # Reset state to unconfigured before attempting to load
        self.config_good = False
        print("Attempting to load RoleRotation config...")

        try:
            # 1. Read config files from disk
            conf_json = self.read_config()
            user_ids = self.read_user_ids()

            # if conf_json is None:
            #     print("Failed to read config file. Aborting load.")
            #     return False
            #
            # if not user_ids:
            #     print("User file is empty or invalid. Aborting load.")
            #     return False

            # 2. Validate config keys
            missing_keys = set(ConfKeys) - set(conf_json.keys())
            if missing_keys:
                message = f"Config file is missing keys: {missing_keys}"
                print(message)
                return KeyError(message)

            # 3. Fetch Discord objects
            role_id = conf_json[ConfKeys.ROLE_ID.value]

            duty_role = self.guild.get_role(role_id)  #todo enable caching? probably dont need to
            if not duty_role:
                duty_role = await self.guild.fetch_role(role_id)  # Fetch if not in cache

            # if not managed_role:
            #     print(f"Could not find Role with ID: {role_id} in Guild {guild.name}")
            #     return False

            # 4. Check bot's permissions
            me = self.guild.get_member(self.client.user.id)
            if not me:
                me = await self.guild.fetch_member(self.client.user.id)

            if me.top_role <= duty_role:
                print(f"Error: Bot's top role is not high enough to manage '{duty_role.name}'")
                return Exception(f"Error: Bot's top role is not high enough to manage '{duty_role.name}'") #todo custom errors?

            # 5. Fetch the members the configuration listed
            users = []
            for user_id in user_ids:
                users.append(await self.guild.fetch_member(user_id))

            # --- SUCCESS ---
            # All data is loaded and validated. Assign to self.
            self.managed_role = duty_role
            self.members = users
            self.member_ids = user_ids

            self.role_id = role_id
            self.index = conf_json[ConfKeys.INDEX.value]
            self.schedule_hour = conf_json[ConfKeys.SCHEDULE_HOUR.value]
            self.schedule_minute = conf_json[ConfKeys.SCHEDULE_MINUTE.value]
            self.schedule_day =  conf_json[ConfKeys.SCHEDULE_DAY.value]

            self.config_good = True
            print("RoleRotation config loaded successfully.")
            self.update_scheduler()
            return None

        except json.JSONDecodeError as e:
            e.add_note("Error in the config file syntax")
            print(e)
            return e
        except (discord.NotFound, discord.Forbidden) as e:
            print(f"Discord API Error: Could not fetch required objects."
                  f"Check the member ids are valid, and that they are in the server."
                  f"Also check bot permissions. It might not have intents or the ability to see a member {e}")
            self.config_good = False
            return e
        except KeyError as e:
            print(f"Config file validation error: {e}")
            self.config_good = False
            return e
        except discord.HTTPException as e:
            e.add_note("There was an unexpected http error")
            self.config_good = False
            return e
        except Exception as e:
            print(f"An unexpected error occurred during config load: {e}")
            self.config_good = False
            return e


    @staticmethod
    def create_default_conf(force=False):
        if not force and CONFIG_FILE_NAME.is_file():
            print("Config file already exists. Use force=True to overwrite.") #todo find a better way
            return

        config = {
            ConfKeys.SCHEDULE_DAY: int(random() * 7),
            ConfKeys.SCHEDULE_HOUR: int(random() * 24),
            ConfKeys.SCHEDULE_MINUTE: int(random() * 60),
            ConfKeys.INDEX: 0,
            ConfKeys.ROLE_ID: 0,
        }

        try:
            with open(CONFIG_FILE_NAME, "w") as file:
                json.dump(config, file, indent=4)
            print(f"Created default config at {CONFIG_FILE_NAME}")
        except PermissionError:
            print(f"I dont have the permissiosn to write to {CONFIG_FILE_NAME}")

    @staticmethod
    def create_default_user_conf(force=False):
        if not force and USERS_FILE_NAME.is_file():
            print("Users file already exists. Use force=True to overwrite.")
            return

        with open(USERS_FILE_NAME, "w") as file:
            file.write("# Just list the member IDs to add them to the rotation, using # for comments.\n"
                       "# The order they are listed is the order of rotation.\n"
                       "123456789012345678  # ExampleUser1\n"
                       "876543210987654321  # ExampleUser2\n"
                       )
        print(f"Created default member file at {USERS_FILE_NAME}")

    @staticmethod
    def read_config() -> Union[dict|None]:
        """Reads the JSON config file and just returns the object."""
        if not CONFIG_FILE_NAME.is_file():
            print("Config file not found, creating a default one...")
            RoleRotation.create_default_conf(force=True)
            return None  # Return None to indicate it needs to be filled out
        with open(CONFIG_FILE_NAME, "r") as confFP:
            return json.load(confFP)



    @staticmethod
    def read_user_ids() -> List[int]:
        """Gets all the member ids from its configuration file. Returns list of ints."""
        user_ids = []
        if not USERS_FILE_NAME.is_file():
            print("Users file not found, creating a default one...")
            RoleRotation.create_default_user_conf(force=True)
            return user_ids  # Return empty list

        comment_re = re.compile(r'^\s*#')
        empty_line_re = re.compile(r'(^\s*$)')
        userid_re = re.compile(r'^\s*(\d+)')  # Capture the digits


        with open(USERS_FILE_NAME, "r") as file:
            for line in file:
                if comment_re.search(line) or empty_line_re.match(line):
                    continue

                userid_match = userid_re.search(line)
                if not userid_match:
                    print(f"Couldn't find a member id on line, skipping: {line.strip()}")
                    continue

                user_id = int(userid_match.group(1))
                if user_id <= 0:
                    print(f"Invalid member id, expected positive number: {line.strip()}")
                    continue

                user_ids.append(user_id)


        return user_ids

    @config_required
    async def clear_role(self):
        """Removes the duty role from all MANAGED members. User must purge roles from members not in the list."""

        print(f"Clearing role '{self.managed_role.name}' from {len(self.members)} members.")
        for member_id in self.member_ids:
            try:
                member = await self.guild.fetch_member(member_id)
                if self.managed_role in member.roles:
                    await member.remove_roles(self.managed_role)

            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"Failed to remove role from {member.name}: {e}")
                return False
        return True

    @config_required
    def write_config(self):

        config = {
            ConfKeys.SCHEDULE_DAY: self.schedule_day,
            ConfKeys.SCHEDULE_HOUR: self.schedule_hour,
            ConfKeys.SCHEDULE_MINUTE: self.schedule_minute,
            ConfKeys.INDEX: self.index,
            ConfKeys.ROLE_ID: self.role_id,

        }
        try:
            with open(CONFIG_FILE_NAME, "w") as fp:
                json.dump(config, fp, indent=4)
        except PermissionError:
            print(f"No permissions to write {CONFIG_FILE_NAME}")

    @config_required
    async def add_user(self, member_id: int) -> Optional[Exception]:

        try:
            member = await self.guild.fetch_member(member_id)
            if member in self.members:
                return Exception(f"This person is already in the rotation {member.name}")
            self.members.append(member)
            self.member_ids.append(member_id)
            with open(USERS_FILE_NAME, "a") as fp:
                fp.write(str(member_id) + "\n")

        except discord.NotFound as e:
            e.add_note("A member with this ID does not exist.")
            return e
        except discord.HTTPException as e:
            return e
        except Exception as e:
            e.add_note("Something really went wrong, this shouldn't have happened")
            print(e)
            return e

        self.member_ids.append(member_id)
        return None

    @config_required
    def remove_user(self, member_id) -> bool:
        comment_re = re.compile(r'^\s*#')
        empty_line_re = re.compile(r'(^\s*$)')
        userid_re = re.compile(r'^\s*(\d+)')  # Capture the digits

        with open(USERS_FILE_NAME, "r") as fp:
            # Read all lines first
            lines = fp.readlines()

        deleted = False

        # We just build a list of lines for a new config. If we hit the match, just skip adding that to the new config
        # That effectively deletes the member from the config
        new_lines = []
        for line in lines:
            if comment_re.search(line) or empty_line_re.search(line):
                new_lines.append(line)
                continue
            cur_user_id = int(userid_re.search(line)[0])
            if member_id == cur_user_id:
                deleted = True
                continue  # skip adding this line (deletes it)
            new_lines.append(line)

        # Only rewrite the file if something was deleted
        if deleted:
            self.member_ids.remove(member_id)
            for i, m in enumerate(self.members):
                if m.id == member_id:
                    del self.members[i]
                    del self.member_ids[i]
                    break
            with open(USERS_FILE_NAME, "w") as fp:
                fp.writelines(new_lines)

        return deleted

    @config_required
    async def rotate_role(self):
        """Rotates the duty role to the next member in the list."""
        if not await self.clear_role():
            print("Failed rotate role because I couldn't clear the role from someone")
            return False

        self.index += 1
        if self.index >= len(self.members):
            self.index = 0

        next_user = self.members[self.index]
        print(f"Rotating role to member: {next_user.name}")
        try:
            await next_user.add_roles(self.managed_role)
            self.write_config()
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"Failed to add role to {next_user.name}: {e}")

        return True

    @config_required
    async def fetch_members(self) -> List[discord.Member]:
        # todo use this in the loader function
        """Re-fetches all managed members from Discord."""

        members = []
        for user_id in self.member_ids:
            try:
                members.append(await self.guild.fetch_member(user_id))
            except (discord.NotFound, discord.HTTPException) as e:
                print(f"Invalidating the config because I Failed to fetch member with ID {user_id}: {e}")
                print("This could also just be issues with the api.")
                self.config_good = False

        self.members = members  # Update internal list
        return members

    @override
    def __str__(self):
        if not self.config_good:
            return "<RoleRotation (Unconfigured)>"

        return (f"<RoleRotation (Configured)>\n"
                f"Guild: {self.guild.name} \n"
                f"Role: {self.managed_role.name} ({self.role_id})\n"
                f"Schedule Days: {self.schedule_day}\n"
                f"Schedule Time: {self.schedule_hour:02d}:{self.schedule_minute:02d}\n"
                f"Current Index: {self.index}\n"
                f"On Duty: {self.members[self.index].name if self.members else 'None'}\n"
                f"Users: {[user.name for user in self.members]}")

    @config_required
    def update_scheduler(self):
        self.scheduler.remove_all_jobs()
        self.scheduler.add_job(
            self.rotate_role,
            trigger='cron',
            day_of_week=self.schedule_day,
            # hour=self.schedule_hour,
            # minute=self.schedule_minute,
            # second="*/15"
        )

