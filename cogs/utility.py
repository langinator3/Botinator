import datetime
import time
import asyncio
import asyncpg
import logging

from discord.ext import commands
import discord

from utils import checks
import config

def pin_check(m):
	return not m.pinned


class Utility:
	def __init__(self, bot):
		self.bot = bot
		self.log_ignore = ['pokemon', 'role-assigning', 'music', 'welcome', 'testing']
		self.attachment_cache = {}

###################
#                 #
# LOGGING         #
#                 #
###################

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

###################
#                 #
# MEMBER          #
#                 #
###################

	async def on_member_join(self, member):
		await self.log(discord.Colour(0x1bb27f), '**[USER JOIN]**', member)

	async def on_member_remove(self, member):
		await self.log(discord.Colour(0x5b0506), '**[USER LEAVE]**', member)

###################
#                 #
# MESSAGE         #
#                 #
###################

	async def on_message_delete(self, message):
		if message.content.startswith(self.bot.command_prefix):
			return
		if message.channel.name in self.log_ignore or await self.bot.is_command(message):
			return
		logging_channel = self.get_logging_channel(message)
		content = message.content
		if message.author.bot and message.channel.id == logging_channel.id:
			try:
				em = message.embeds[0]
			except:
				em = None
			await logging_channel.send(':x: **[LOG DELETED]**\n*{0}*\n{1}'.format(datetime.datetime.utcnow(), content), embed=em)
		else:
			if not message.author.bot:
				try:
					em = message.embeds[0]
					content += '\n__*Embed message*__'
				except:
					pass
				try:
					attach = message.attachments[0]
					content += '\n**Attachments:**\n{0.filename} {0.url}'.format(attach)
				except:
					pass
				description = ':x: **[MESSAGE DELETED]**\n{0}\n{1}'.format(message.channel.mention, content)
				await self.log(discord.Colour.red(), description, message.author)
		if message.author.bot:
			pass
		
	async def on_message_edit(self, message, edit):
		if message.author.bot or message.content == edit.content or \
				message.channel.name in self.log_ignore:
			return
		logging_channel = self.get_logging_channel(message)
		if logging_channel is None:
			return
		member = message.author
		em = discord.Embed(colour=discord.Colour.gold())
		em.set_author(name=str(member), icon_url=member.avatar_url)
		em.timestamp = datetime.datetime.utcnow()
		if len(message.content) + len(edit.content) >= 1964:
			em.description = '**[MESSAGE EDITED 1/2]**\n{0.channel.mention}\n**OLD ⮞** {0.content}'.format(message)
			await logging_channel.send(embed=em)
			em.description = '**[MESSAGE EDITED 2/2]**\n{0.channel.mention}\n**NEW ⮞** {0.content}'.format(edit)
			await logging_channel.send(embed=em)
		else:
			em.description = '**[MESSAGE EDITED]**\n{0.channel.mention}\n**OLD ⮞** {0.content}\n**NEW ⮞**' \
								' {1.content}'.format(message, edit)
			await logging_channel.send(embed=em)

###################
#                 #
# COGS            #
#                 #
###################

	@commands.command(hidden=True, name='reload')
	@commands.is_owner()
	async def reloader(self, ctx, *, ext):
		"""Reload a cog."""
		if not ext.startswith('cogs.'):
			ext = f'cogs.{ext}'
		try:
			self.bot.unload_extension(ext)
		except:
			pass
		try:
			self.bot.load_extension(ext)
		except Exception as e:
			await ctx.send(f'`{e}`',  delete_after=60)
		else:
			await ctx.send(f'Cog {ext} reloaded.',  delete_after=60)

	@commands.command(hidden=True, name='load')
	@commands.is_owner()
	async def loader(self, ctx, *, ext):
		"""Load a cog."""
		if not ext.startswith('cogs.'):
			ext = f'cogs.{ext}'
		try:
			self.bot.load_extension(ext)
		except Exception as e:
			await ctx.send(f'`{e}`',  delete_after=60)
		else:
			await ctx.send(f'Cog {ext} loaded.',  delete_after=60)

	@commands.command(hidden=True, name='unload')
	@commands.is_owner()
	async def unloader(self, ctx, *, ext):
		"""Unload a cog."""
		if not ext.startswith('cogs.'):
			ext = f'cogs.{ext}'
		try:
			self.bot.unload_extension(ext)
		except:
			await ctx.send(f'Cog {ext} is not loaded.',  delete_after=60)
		else:
			await ctx.send(f'Cog {ext} unloaded.',  delete_after=60)

###################
#                 #
# MISCELLANEOUS   #
#                 #
###################

		# Sets the playing feature of the bot
	@commands.command(name='setplaying')
	@checks.admin_or_permissions(administrator=True)
	async def set_playing(self, ctx, *, status: str = '#PMA'):
		"""Sets the 'Playing' message for the bot."""
		await self.bot.change_presence(game=discord.Game(name=status))

		# Shows Uptime of the Server
	@commands.command(name='uptime')
	async def bot_uptime(self, ctx):
		"""Shows the bots uptime"""
		up = abs(self.bot.uptime - int(time.perf_counter()))
		up = datetime.timedelta(seconds=up)
		await ctx.send(f'`Uptime: {up}`', delete_after=60)

	@commands.command(name='userinfo' , aliases=['user', 'uinfo', 'info', 'ui'])
	async def user_info(self, ctx, *, name=""):
		"""Get user info. Ex: `!info @user`"""
		if name:
			try:
				user = ctx.message.mentions[0]
			except IndexError:
				user = ctx.guild.get_member_named(name)
			if not user and name.isdigit():
				user = ctx.guild.get_member(int(name))
			if not user:
				await ctx.send(self.bot.bot_prefix + 'Could not find user.')
				return
		else:
			user = ctx.message.author

		# Thanks to IgneelDxD for help on this
		if user.avatar_url[54:].startswith('a_'):
			avi = 'https://images.discordapp.net/avatars/' + user.avatar_url[35:-10]
		else:
			avi = user.avatar_url

		role = user.top_role.name
		if role == "@everyone":
			role = "N/A"
		if not user.voice:
			voice_state = None
		else:
			voice_state = user.voice.channel
			
		em = discord.Embed(timestamp=ctx.message.created_at, colour=0x708DD0)
		em.add_field(name='User ID', value=user.id, inline=True)
		em.add_field(name='Nick', value=user.nick, inline=True)
		em.add_field(name='Status', value=user.status, inline=True)
		em.add_field(name='In Voice', value=voice_state, inline=True)
		em.add_field(name='Game', value=user.game, inline=True)
		em.add_field(name='Highest Role', value=role, inline=True)
		em.add_field(name='Account Created', value=user.created_at.__format__('%A, %d. %B %Y @ %H:%M:%S'))
		em.add_field(name='Join Date', value=user.joined_at.__format__('%A, %d. %B %Y @ %H:%M:%S'))
		em.set_thumbnail(url=avi)
		em.set_author(name=user, icon_url='https://i.imgur.com/RHagTDg.png')
		await ctx.send(embed=em, delete_after=60)

		
	@checks.no_delete
	@commands.command(hidden=True)
	async def ping(self, ctx):
		"""Pings the bot"""
		channel = ctx.message.channel
		t1 = time.perf_counter()
		await ctx.trigger_typing()
		t2 = time.perf_counter()
		embed=discord.Embed(title=None, description='Pong: {}'.format(round((t2-t1)*1000)), color=0x2874A6)
		await ctx.send(embed=embed, delete_after=60)

def setup(bot):
	bot.add_cog(Utility(bot))
