import json
from enum import Enum
from operator import index
from pathlib import (Path)
from random import random
from typing import override, List, Optional

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import functools
import asyncio

from discord.ext.commands.parameters import empty


class Days(int, Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class ConfKeys(str, Enum):
    ROLE_ID = "role_id"
    SCHEDULE_DAY = "schedule_day"
    SCHEDULE_HOUR = "schedule_hour"
    SCHEDULE_MINUTE = "schedule_minute"
    INDEX = "index"
    MEMBER_IDS = "member_ids"



CONFIG_FILE_NAME = Path("./conf.json")


# def config_required(func):
#     """
#     A decorator that stops a method from running if self.config_good is False.
#     Handles both synchronous and asynchronous methods.
#     """
#
#     @functools.wraps(func)
#     async def async_wrapper(self, *args, **kwargs):
#         # The 'self' argument is the instance of RoleRotation
#         if not self.config_good:
#             print(f"Cannot run '{func.__name__}': Config is not loaded. Please run load_config().")
#             return None
#         return await func(self, *args, **kwargs)
#
#     @functools.wraps(func)
#     def sync_wrapper(self, *args, **kwargs):
#         # The 'self' argument is the instance of RoleRotation
#         if not self.config_good:
#             print(f"Cannot run '{func.__name__}': Config is not loaded. Please run load_config().")
#             return None
#         return func(self, *args, **kwargs)
#
#     # Return the correct wrapper based on whether the original function was async
#     if asyncio.iscoroutinefunction(func):
#         return async_wrapper
#     else:
#         return sync_wrapper


# Manages the list of member_ids to rotate into duty, and the configuration for the app
# You MUST await load_config before using this class
class RoleRotation:
    """
    Manages the rotation of a Discord role among a list of members.
    Unless otherwise noted, all functions immediately rewrite the entire config on change

    Usage:
    1. Instanciate
    2. After the async loop, call load_config
    """

    def __init__(self, client: discord.Client, guild_id: int):
        """Initializes the RoleRotation object in an unconfigured state."""

        # Doesnt do much because we either need:
        # to be logged in with the discord button
        # or otherwise require the asyncio loop

        # --- Config State ---
        self.config_good: bool = False  # Is false before running load_conf() or after load_conf() failed
        self.scheduler = AsyncIOScheduler()
        self.guild_id: int = guild_id
        self.client = client

        # --- Fetched Discord Objects ---
        self.managed_role: discord.Role = None
        self.members: List[discord.Member] = []
        self.guild: discord.Guild = None

        # --- Config File Values ---
        self.role_id: Optional[int] = None
        self.index: int = 0
        self.schedule_day: int = 0
        self.schedule_hour: int = 0
        self.schedule_minute: int = 0

    # todo finish error handling here
    async def load_config(self) -> Optional[Exception]:
        """
        Loads configuration from disk and fetches required Discord objects.
        This method fully populates the object's state, and (re)starts the scheduler

        If something is malformed, a flag is set to invalidate the configuration for @config_required
        """

        if self.guild is None:
            # Only runs on first call to load_config: the first time after the bot logs in
            self.guild = await self.client.fetch_guild(self.guild_id)

        # Reset state to unconfigured before attempting to load
        self.config_good = False
        print("Attempting to load RoleRotation config...")

        try:
            # 1. Read config files from disk
            conf_json = self.read_config()

            # 2. Validate config keys
            missing_keys = set(ConfKeys) - set(conf_json.keys())
            if missing_keys:
                message = f"Config file is missing keys: {missing_keys}"
                print(message)
                return KeyError(message)

            # 3. Fetch Role and validate bot permissions
            role_id = conf_json[ConfKeys.ROLE_ID.value]
            role = await self.guild.fetch_role(role_id)  # Fetch if not in cache
            me = self.guild.get_member(self.client.user.id)
            if not me:
                me = await self.guild.fetch_member(self.client.user.id)
            if me.top_role <= role:
                print(f"Error: Bot's top role is not high enough to manage '{role.name}'")
                return Exception(
                    f"Error: Bot's top role is not high enough to manage '{role.name}'")  # todo custom errors?


            # 4. Fetch members
            # Cant use the method since that requires config to be loaded.
            users = []
            for member_id in conf_json[ConfKeys.MEMBER_IDS]:
                users.append(await self.guild.fetch_member(member_id))

            # --- SUCCESS ---
            # All data is loaded and validated. Assign to self.
            self.managed_role = role
            self.members = users

            self.role_id = role_id
            self.index = conf_json[ConfKeys.INDEX.value]
            self.schedule_hour = conf_json[ConfKeys.SCHEDULE_HOUR.value]
            self.schedule_minute = conf_json[ConfKeys.SCHEDULE_MINUTE.value]
            self.schedule_day = conf_json[ConfKeys.SCHEDULE_DAY.value]

            if self.members is empty:
                print("There is no one in the list. Leaving config invalid to prevent index error.")
            else:
                try:
                    self.members[self.index]
                except IndexError as e:
                    print("The index in conf was somehow out of range. What was the last command you ran?")
                    print("Are there any people in the list?")
                    return e

                self.config_good = True
                print("RoleRotation config loaded successfully.")
                self.retrigger_scheduler()
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

    def create_default_conf(force=False):
        """Creates a default config file"""
        if not force and CONFIG_FILE_NAME.is_file():
            print("Config file already exists. Use force=True to overwrite.")  # todo find a better way
            return

        config = {
            ConfKeys.SCHEDULE_DAY: int(random() * 7),
            ConfKeys.SCHEDULE_HOUR: int(random() * 24),
            ConfKeys.SCHEDULE_MINUTE: int(random() * 60),
            ConfKeys.INDEX: 0,
            ConfKeys.ROLE_ID: 1328808733706293419,
            ConfKeys.MEMBER_IDS: [
                123456789012345567,
                123456789012345567,
                123456789012345567
            ]
        }

        try:
            with open(CONFIG_FILE_NAME, "w") as file:
                json.dump(config, file, indent=4)
            print(f"Created default config at {CONFIG_FILE_NAME}")
        except PermissionError:
            print(f"I dont have the permission to write to {CONFIG_FILE_NAME}")

    @staticmethod
    def read_config() -> dict:
        """Reads the JSON config file and just returns the object."""
        if not CONFIG_FILE_NAME.is_file():
            print("Config file not found, creating a default one...")
            RoleRotation.create_default_conf()
            raise FileNotFoundError("There was no config, created a default one instead")  # Return None to indicate it needs to be filled out

        with open(CONFIG_FILE_NAME, "r") as confFP:
            return json.load(confFP)


    async def clear_role(self):
        """
        Removes the role from all MANAGED members. A member not listed in configuration is unaffected.
        """

        print(f"Clearing role '{self.managed_role.name}' from {len(self.members)} members.")
        await self.fetch_members()
        for member in self.members:
            if self.managed_role in member.roles:
                # http status 204 mean it was successful and has nothing else to say
                await member.remove_roles(self.managed_role)


    # @config_required
    def write_config(self, force=False):
        if self.config_good or force:
            #todo forcing this could never cause a fatal error right?

            print("writing config")
            config = {
                ConfKeys.SCHEDULE_DAY: self.schedule_day,
                ConfKeys.SCHEDULE_HOUR: self.schedule_hour,
                ConfKeys.SCHEDULE_MINUTE: self.schedule_minute,
                ConfKeys.INDEX: self.index,
                ConfKeys.ROLE_ID: self.role_id,
                ConfKeys.MEMBER_IDS: list(member.id for member in self.members)

            }

            with open(CONFIG_FILE_NAME, "w") as fp:
                json.dump(config, fp, indent=4)
            print("wrote config")




    async def add_user(self, member_id: int, position: int=-1):
        """
        Adds a user to the botton of the rotation.
        Returns the user if they were successfully added and moved (if applicable)
        """
        #todo why does remove user have no error handling, but this function does?. Should they match?
        print("Appending user")
        try:
            new_member = await self.guild.fetch_member(member_id)
            if new_member in self.members:
                raise Exception(f"This person is already in the rotation {new_member.name}")
            self.members.append(new_member)
            try:
                self.write_config()
            except Exception as e:
                print("Failed")
                await self.load_config()
                e.add_note("Failed to write to config after adding a user. Who ever you just tried to add didnt get saved")
                raise e

        except discord.NotFound as e:
            e.add_note("A member with this ID does not exist.")
            return None
        except discord.Forbidden as e:
            e.add_note("Cannot add a user who is not in this guild")
            return None

        if position != -1:
            try:
                self.move_member(new_member, position)
            except Exception as e:
                e.add_note("Successfully added a user, but couldn't move them to the position specified.")
                raise e
        return new_member

    def remove_user(self, member_id):

        deleted = None
        # If we delete the user who is on duty we need to notify the user
        if self.members[self.index].id == member_id:
            raise Exception("Cannot delete the user who is currently on duty")
        for i, m in enumerate(self.members):
            if member_id == m.id:
                if i <= self.index:
                    self.index = self.index-1
                deleted = self.members.pop(i)
                self.write_config()
                print("wrote config")
                break

        if self.members is empty:
            self.config_good = False
            raise Exception("Successfully deleted, but now there is no one left in the list. Add someone and reload.")

        return deleted

    async def rotate_role(self):
        """Rotates the duty role to the next member in the list."""
        print("Attempting to clear the roles")
        await self.clear_role()

        self.index += 1
        if self.index >= len(self.members):
            self.index = 0

        next_user = self.members[self.index]
        print(f"Rotating role to member: {next_user.name}")
        await next_user.add_roles(self.managed_role)

        try:
            self.write_config()
        except Exception as e:
            e.add_note("Failed to write config to disk while rotating. The index is probably wrong right now.")
            raise e

    def set_index(self, i: int, force=False):
        if self.config_good:
            print("changing the index to " + i.__str__())
            old_member = self.members[self.index]
            new_member = self.members[i]
            if old_member == new_member: return

            self.clear_role()
            self.index = i
            new_member.add_roles(self.managed_role)
            self.write_config()
        elif force:
            self.index = i
            self.write_config(force=True)
            print("Forcibly changed the index, will need a reload")

        else: raise Exception("Tried to run this command without forcing it, but with unconfigured config")

    async def fetch_members(self) -> List[discord.Member]:
        # todo use this in the loader function
        """Re-fetches all managed members from Discord."""

        members = []
        for member in self.members:
            mem_id = member.id
            try:
                members.append(await self.guild.fetch_member(mem_id))
            except Exception as e:
                e.add_note("Failed to fetch members for some reason")
                self.config_good = False
                raise e

        self.members = members
        return members

    def move_member(self, member: discord.Member, position: int):
        if position < 0 or position > len(self.members)-1:
            raise Exception(f"Tried to move to an out-of-range index. Max is {len(self.members) - 1}")

        cur_pos = self.members.index(member)
        if cur_pos == -1:
            raise Exception("Tried to move a member who is not listed in config")
        if cur_pos == position:
            return # They arent moving it anywhere lol

        # Deleting, then inserting into the correct position
        _ = self.members.pop(cur_pos) # The function argument is likely a more recent fetch
        if position == len(self.members)-1: # They specified the last index, so just append it
            self.members.append(member)
        elif position < cur_pos: # Indexes to the left are unaffected when we remove an item
            self.members.insert(position, member)
        else: # indexes to the right are left shifted when we remove
            self.members.insert(position-1, member)


    @override
    def __str__(self):
        # todo this will definetly throw errors when the config isnt configured... but it needs to not
        return (f"<RoleRotation (Configured)>\n"
                f"Guild id: {self.guild_id} \n"
                f"Guild: {self.guild} \n"                
                f"Role: {self.role_id} ({self.managed_role})\n"
                f"Schedule Days: {self.schedule_day}\n"
                f"Schedule Time: {self.schedule_hour:02d}:{self.schedule_minute:02d}\n"
                f"Current Index: {self.index}\n"
                f"Members: {list(m.name for m in self.members)}"
                )
                # f"On Duty: {self.members[self.index].name if self.members else 'None'}\n"
                # f"Users: {[user.name for user in self.members]}")

    def retrigger_scheduler(self):
        """Must be called after reloading config from disk. Updates the scheduler to match is stored in the class"""

        self.scheduler.remove_all_jobs()
        self.scheduler.add_job(
            self.rotate_role,
            trigger='cron',
            day_of_week=self.schedule_day,
            hour=self.schedule_hour,
            minute=self.schedule_minute,
        )

    def set_new_schedule(self, day=-1, hour=-1, minute=-1):
        self.schedule_day = self.schedule_day if day == -1 else day
        self.schedule_hour = self.schedule_hour if hour == -1 else hour
        self.schedule_minute = self.schedule_minute if minute == -1 else minute

        self.write_config()
        self.retrigger_scheduler()

