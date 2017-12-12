import asyncio

import datetime
import time

from discord.ext import commands
import discord

from utils import checks

sellout_cooldown = 7200

###################
#                 #
# WELCOME         #
#                 #
###################


class Welcome:
	def __init__(self, bot):
		self.bot = bot

	def get_role_member(self, guild):
		if guild is None:
			return None
		return discord.utils.get(guild.roles, name='Member')

	async def get_welcome_channel(self, guild, *, channel_id=None, con=None):
		if guild is None:
			return None
		if con:
			channel_id = await con.fetchval('''
				SELECT channel_id FROM greetings WHERE guild_id = $1
				''', guild.id)
		channel = None
		if channel_id:
			channel = discord.utils.get(guild.channels, id=channel_id)
		return channel or discord.utils.get(guild.channels, name='welcome')

		# Welcome Main Command
	@checks.db
	@commands.group()
	@checks.admin_or_permissions(manage_guild=True)
	async def welcome(self, ctx):
		"""Sets welcome module settings."""
		guild = ctx.guild
		async with ctx.con.transaction():
			settings = await ctx.con.fetchrow('''
				INSERT INTO greetings (guild_id) VALUES ($1)
				ON CONFLICT (guild_id) DO
				UPDATE SET guild_id = $1 RETURNING *
				''', ctx.guild.id)
		if ctx.invoked_subcommand is None:
			msg = ['```']
			msg.append(f"Enabled: {settings['enabled']}")
			channel = await self.get_welcome_channel(ctx.guild, channel_id=settings['channel_id'])
			msg.append(f'Channel: {channel.mention if channel else None}')
			msg.append(f"Message: {settings['message']}")
			msg.append('```')
			await ctx.send('\n'.join(msg), delete_after=30)

		# Sub-command to set welcome greeting
	@checks.db
	@checks.no_delete
	@welcome.command(aliases=['message'])
	async def setgreeting(self, ctx, *, format_msg = None):
		"""Sets the welcome message format for the server.
		{0.name} is user. {1.name} is server"""
		if format_msg is None:
			await self.bot.send_help(ctx)
			return
		async with ctx.con.transaction():
			await ctx.con.execute('''
				UPDATE greetings SET message = $1 WHERE guild_id = $2
				''', format_msg, ctx.guild.id)
		await ctx.send('Welcome message set for the server.', delete_after=30)
		await self.send_testing_msg(ctx)

		# Sub-command to toggle
	@checks.db
	@welcome.command()
	async def toggle(self, ctx, enable: bool=None):
		"""Turns on/off welcoming new users to the server."""
		guild = ctx.guild
		async with ctx.con.transaction():
			before = await ctx.con.fetchval('''
				SELECT enabled FROM greetings WHERE guild_id = $1
				''', guild.id)
			if enable is None or enable != before:
				after = await ctx.con.fetchval('''
					UPDATE greetings SET enabled = NOT enabled WHERE guild_id = $1 RETURNING enabled
					''', guild.id)
			else:
				after = before
		if after == before:
			if after:
				await ctx.send('Welcome message is already enabled.', delete_after=30)
			else:
				await ctx.send('Welcome message is already disabled.', delete_after=30)
		elif after:
			await ctx.send('I will now welcome new users to the server.', delete_after=30)
			await self.send_testing_msg(ctx)
		else:
			await ctx.send('I will no longer welcome new users.', delete_after=30)

		# Sub-command to set welcome channel
	@checks.db
	@welcome.command()
	async def setchannel(self, ctx, channel: discord.TextChannel=None):
		"""Sets the channel for welcoming new users."""
		guild = ctx.guild
		channel = channel or ctx.channel
		async with ctx.con.transaction():
			await ctx.con.execute('''
				UPDATE greetings SET channel_id = $1 WHERE guild_id = $2
				''', channel.id, guild.id)
		await ctx.send(f'Set {channel.mention} as welcome channel.', delete_after=30)

	async def on_member_join(self, member):
		guild = member.guild
		async with self.bot.db_pool.acquire() as con:
			settings = await con.fetchrow('''
				SELECT * FROM greetings WHERE guild_id = $1
				''', guild.id)
		channel = await self.get_welcome_channel(guild, channel_id=settings['channel_id'])
		member_role = self.get_role_member(guild)
		if not settings['enabled']:
			return
		if channel is not None:
			await channel.send(settings['message'].format(member, guild))
		if member_role is not None:
			await member.add_roles(member_role)

	async def send_testing_msg(self, ctx):
		guild = ctx.guild
		async with self.bot.db_pool.acquire() as con:
			settings = await con.fetchrow('''
				SELECT * FROM greetings WHERE guild_id = $1
				''', guild.id)
		con = getattr(ctx, 'con', None)
		local = con is None
		if local:
			con = await self.bot.db_pool.acquire()
		try:
			channel = await self.get_welcome_channel(guild, con=con)
		finally:
			if local:
				await self.bot.db_pool.release(con)
		if channel is not None:
			await ctx.channel.send(f'Sending a testing message to {channel.mention}', delete_after=30)
			try:
				await channel.send(settings['message'].format(ctx.author, guild))
			except discord.DiscordException as e:
				await ctx.channel.send(f'`{e}`')
		else:
			await ctx.channel.send('Neither the set channel nor channel named "welcome" exists.', delete_after=30)


def setup(bot):
	bot.add_cog(Welcome(bot))
