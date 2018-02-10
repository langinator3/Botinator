from discord.ext import commands
from utils import checks
from collections import Counter, defaultdict
from inspect import cleandoc

import re
import discord
import datetime
import asyncio
import asyncpg
import argparse, shlex
import logging
import random

def pin_check(m):
    return not m.pinned

## Converters

class MemberID(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            m = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                return int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(f"{argument} is not a valid member or member ID.") from None
        else:
            can_execute = ctx.author.id == ctx.bot.owner_id or \
                        ctx.author == ctx.guild.owner or \
                        ctx.author.top_role > m.top_role

            if not can_execute:
                raise commands.BadArgument('You cannot do this action on this user due to role hierarchy.')
            return m.id

class Mod:
    """Moderation related commands."""

    def __init__(self, bot):
        self.bot = bot
        self.purge_task = self.bot.loop.create_task(self.purge())
        self.log_ignore = ['pokemon', 'role-assigning', 'music', 'welcome', 'testing']
        self.purge_ignore = ['logs']
        self.attachment_cache = {}

    def __unload(self):
        self.purge_task.cancel()

    def get_role_muted(self, guild):
        if guild is None:
            return None
        return discord.utils.get(guild.roles, name='MUTED')

    def get_logging_channel(self, ctx):
        if ctx.guild is None:
            return None
        return discord.utils.get(ctx.guild.channels, name='logs')

    async def log(self, color, content, author, timestamp=None):
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()
        em = discord.Embed(colour=color, description=content, timestamp=timestamp)
        em.set_author(name=str(author), icon_url=author.avatar_url)
        try:
            await self.get_logging_channel(author).send(embed=em)
        except AttributeError:
            pass

    async def __error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if isinstance(original, discord.Forbidden):
                await ctx.send('I do not have permission to execute this action.')
            elif isinstance(original, discord.NotFound):
                await ctx.send(f'This entity does not exist: {original.text}')
            elif isinstance(original, discord.HTTPException):
                await ctx.send('Somehow, an unexpected error occurred. Try again later?')

###################
#                 #
# CHAT            #
#                 #
###################

    async def banned_words(self, message):
        banned_words = ['dadddy', 'daddy', 'dady',
                        'dadddi', 'daddi', 'dadi',
                        'papa', 'papi',
                        ':/', ': /', ';/',
                        '¯\_(ツ)_/¯',
                        'oof'
                        ]
        if banned_words is None:
            banned_words = []

        words = list(map(lambda w: w.lower(), message.content.split()))
        for banned_word in banned_words:
            if banned_word.lower() in words:
                await message.delete()
                banned_phrase = ["**LANGUAGE!!!** 😡", "See that word, **DELETED**", "**Chill**", "That word has been shuckled", "You fuckled with the :Shuckle:", "BREEEEEEEEEEEEEEEEEEEEEEEEEEE"]
                msg = await message.channel.send(f"{message.author.mention}, {random.choice(banned_phrase)}", delete_after=30)

    async def on_message_edit(self, before, after):
        await self.banned_words(after)

    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return
        await self.banned_words(message)

###################
#                 #
# MODERATION      #
#                 #
###################

    @commands.command()
    @commands.guild_only()
    @checks.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason = None):
        """Kicks a member from the server.

        In order for this to work, the bot must have Kick Member permissions.

        To use this command you must have Kick Members permission.
        """

        if reason is None:
            reason = f'Action done by {ctx.author} (ID: {ctx.author.id})'

        await member.kick(reason=reason)
        await ctx.send('\N{OK HAND SIGN}')

    @commands.command()
    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    async def ban(self, ctx, member: MemberID, *, reason = None):
        """Bans a member from the server.

        You can also ban from ID to ban regardless whether they're
        in the server or not.

        In order for this to work, the bot must have Ban Member permissions.

        To use this command you must have Ban Members permission.
        """

        if reason is None:
            reason = f'Action done by {ctx.author} (ID: {ctx.author.id})'

        await ctx.guild.ban(discord.Object(id=member), reason=reason)
        await ctx.send('\N{OK HAND SIGN}')

    @commands.command()
    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    async def massban(self, ctx, reason, *members: MemberID):
        """Mass bans multiple members from the server.

        You can also ban from ID to ban regardless whether they're
        in the server or not.

        Note that unlike the ban command, the reason comes first
        and is not optional.

        In order for this to work, the bot must have Ban Member permissions.

        To use this command you must have Ban Members permission.
        """

        for member_id in members:
            await ctx.guild.ban(discord.Object(id=member_id), reason=reason)

        await ctx.send('\N{OK HAND SIGN}')

    @commands.command()
    @commands.guild_only()
    @checks.has_permissions(kick_members=True)
    async def softban(self, ctx, member: MemberID, *, reason = None):
        """Soft bans a member from the server.

        A softban is basically banning the member from the server but
        then unbanning the member as well. This allows you to essentially
        kick the member while removing their messages.

        In order for this to work, the bot must have Ban Member permissions.

        To use this command you must have Kick Members permissions.
        """

        if reason is None:
            reason = f'Action done by {ctx.author} (ID: {ctx.author.id})'

        obj = discord.Object(id=member)
        await ctx.guild.ban(obj, reason=reason)
        await ctx.guild.unban(obj, reason=reason)
        await ctx.send('\N{OK HAND SIGN}')

    @commands.command()
    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    async def unban(self, ctx, member, *, reason = None):
        """Unbans a member from the server.

        You can pass either the ID of the banned member or the Name#Discrim
        combination of the member. Typically the ID is easiest to use.

        In order for this to work, the bot must have Ban Member permissions.

        To use this command you must have Ban Members permissions.
        """

        if reason is None:
            reason = f'Action done by {ctx.author} (ID: {ctx.author.id})'

        await ctx.guild.unban(member.user, reason=reason)
        if member.reason:
            await ctx.send(f'Unbanned {member.user} (ID: {member.user.id}), previously banned for {member.reason}.')
        else:
            await ctx.send(f'Unbanned {member.user} (ID: {member.user.id}).')

###################
#                 #
# PLONKING        #
#                 #
###################

        # Blacklist Command
    @checks.db
    @checks.admin()
    @commands.command(name='mute', aliases=['cuck', 'fuck', 'plonk'])
    async def user_plonk(self, ctx, user: discord.Member, reason: str='being toxic'):
        """Adds a user to the bot's blacklist"""
        try:
            async with ctx.con.transaction():
                await ctx.con.execute('''
                    INSERT INTO plonks (guild_id, user_id) VALUES ($1, $2)
                    ''', ctx.guild.id, user.id)
        except asyncpg.UniqueViolationError:
            await ctx.send('**{0.name}** is already muted.'.format(user),  delete_after=15)
        else:
            muted_role = self.get_role_muted(ctx.guild)
            if muted_role is not None:
                await user.add_roles(muted_role)
            await ctx.send('**{0.mention}** has been muted.'.format(user))
            await self.log(discord.Colour(0xFF5733), "Muted user {0.name}({0.id}) due to **{1}**.".format(user, reason), ctx.author)


            
        # Unblacklist Command
    @checks.db
    @checks.admin()
    @commands.command(name='unmute', aliases=['uncuck', 'unfuck', 'unplonk'])
    async def user_unplonk(self, ctx, user: discord.Member, reason: str='appeal'):
        """Removes a user from the bot's blacklist"""
        async with ctx.con.transaction():
            res = await ctx.con.execute('''
                DELETE FROM plonks WHERE guild_id = $1 and user_id = $2
                ''', ctx.guild.id, user.id)
        deleted = int(res.split()[-1])
        if deleted:
            muted_role = self.get_role_muted(ctx.guild)
            if muted_role is not None:
                await user.remove_roles(muted_role)
            await ctx.send('**{0.mention}** is no longer muted.'.format(user))
            await self.log(discord.Colour(0x096b46), "Unmuted user {0.name}({0.id}) due to **{1}**.".format(user, reason), ctx.author)
        else:
            await ctx.send('**{0.name}** is not muted.'.format(user),  delete_after=15)

###################
#                 #
# CLEANER         #
#                 #
###################

    async def purge(self):
        await self.bot.wait_until_ready()
        channels = [chan for chan in self.bot.get_all_channels() if chan.name in ('role-assigning', 'music', 'pokemon','bot-spam')]
        while not self.bot.is_closed():
            await asyncio.gather(*[chan.purge(limit=300, check=pin_check) for chan in channels], loop=self.bot.loop)
            await asyncio.sleep(3600, loop=self.bot.loop)

###################
#                 #
# CLEANUP         #
#                 #
###################

        # Cleanup Messages Command
    @commands.command(invoke_without_command=True, name='purge', aliases=['clean', 'cleanup', 'delete', 'del'])
    @checks.mod_or_permissions(manage_messages=True)
    async def messages_cleaner(self, ctx, number: int = 1, *, user: discord.Member = None):
        """Deletes last X messages [user]."""
        if ctx.message.channel.name in self.purge_ignore and not ctx.message.author.id in config.owner_ids:
            return
        if number < 1:
            number = 1
        elif isinstance(user, discord.Member):
            def is_user(m):
                return m.id == ctx.message.id or m.author == user
            try:
                await ctx.channel.purge(limit=number + 1, check=is_user)
                await self.log(discord.Colour(0x6666CC), "{0.name}({0.id}) deleted {1} messages made by {2.name}({2.id}) in channel {3}".format(ctx.author, number, user, ctx.channel.mention), ctx.author)
                return
            except discord.errors.Forbidden:
                await ctx.send('I need permissions to manage messages in this channel.',  delete_after=120)
                return
        elif isinstance(number, int):
            try:
                await ctx.channel.purge(limit=number + 1, check=pin_check)
                await self.log(discord.Colour(0x6666CC), "{0.name}({0.id}) deleted {1} messages in channel {2}".format(ctx.author, number, ctx.channel.mention), ctx.author)
                return
            except discord.errors.Forbidden:
                await ctx.send('I need permissions to manage messages in this channel.',  delete_after=120)

def setup(bot):
    bot.add_cog(Mod(bot))
