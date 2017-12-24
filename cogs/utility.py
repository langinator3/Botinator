import datetime
import time
import asyncio
import asyncpg
import logging

from discord.ext import commands
import discord

from utils import checks


def pin_check(m):
	return not m.pinned


class Utility:
	def __init__(self, bot):
		self.bot = bot
		self.purge_task = self.bot.loop.create_task(self.purge())
		self.log_ignore = ['pokemon', 'role-assigning', 'music', 'welcome']
		self.purge_ignore = ['logs']
		self.attachment_cache = {}

	def __unload(self):
		self.purge_task.cancel()
		
		
		
	def get_role_muted(self, guild):
		if guild is None:
			return None
		return discord.utils.get(guild.roles, name='MUTED🔇')

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
# LOGGING         #
#                 #
###################

	def get_logging_channel(self, ctx):
		if ctx.guild is None:
			return None
		return discord.utils.get(ctx.guild.channels, name='logs')

	async def log(self, color, content, author, timestamp=None):
		timestamp = timestamp or datetime.datetime.utcnow()
		em = discord.Embed(colour=color, description=content, timestamp=timestamp)
		em.set_author(name=str(author), icon_url=author.avatar_url)
		try:
			await self.get_logging_channel(author).send(embed=em)
		except AttributeError:
			pass

	async def on_member_join(self, member):
		await self.log(discord.Colour(0x1bb27f), '**[USER JOIN]**', member)

	async def on_member_remove(self, member):
		await self.log(discord.Colour(0x5b0506), '**[USER LEAVE]**', member)
		
	async def on_message_delete(self, message):
		if message.channel.name in self.log_ignore or await self.bot.is_command(message):
			return
		logging_channel = self.get_logging_channel(message)
		content = message.content
		if message.channel.id == logging_channel.id:
			try:
				em = message.embeds[0]
			except:
				em = None
			await logging_channel.send(':x: **[LOG DELETED]**\n*{0}*\n{1}'.format(datetime.datetime.utcnow(), content), embed=em)
		else:
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
# PLONKING        #
#                 #
###################

		# Blacklist Command
	@checks.db
	@checks.admin()
	@commands.command(aliases=['mute'])
	async def plonk(self, ctx, user: discord.Member, reason: str='being toxic'):
		"""Adds a user to the bot's blacklist"""
		try:
			async with ctx.con.transaction():
				await ctx.con.execute('''
					INSERT INTO plonks (guild_id, user_id) VALUES ($1, $2)
					''', ctx.guild.id, user.id)
		except asyncpg.UniqueViolationError:
			await ctx.send('**{0.name}** is already plonked.'.format(user),  delete_after=15)
		else:
			muted_role = self.get_role_muted(ctx.guild)
			logging_channel = self.get_logging_channel(ctx.message)
			if muted_role is not None:
				await user.add_roles(muted_role)
			await ctx.send('**{0.name}** has been plonked.'.format(user),  delete_after=30)
			await self.log(discord.Colour(0xFF5733), "Plonked user {0.name}({0.id}) due to **{1}**.".format(user, reason), ctx.author)


			
		# Unblacklist Command
	@checks.db
	@checks.admin()
	@commands.command(aliases=['unmute'])
	async def unplonk(self, ctx, user: discord.Member, reason: str='appeal'):
		"""Removes a user from the bot's blacklist"""
		async with ctx.con.transaction():
			res = await ctx.con.execute('''
				DELETE FROM plonks WHERE guild_id = $1 and user_id = $2
				''', ctx.guild.id, user.id)
		deleted = int(res.split()[-1])
		if deleted:
			muted_role = self.get_role_muted(ctx.guild)
			logging_channel = self.get_logging_channel(ctx.message)
			if muted_role is not None:
				await user.remove_roles(muted_role)
			await ctx.send('**{0.name}** is no longer plonked.'.format(user),  delete_after=30)
			await self.log(discord.Colour(0x096b46), "Unplonked user {0.name}({0.id}) due to **{1}**.".format(user, reason), ctx.author)
		else:
			await ctx.send('**{0.name}** is not plonked.'.format(user),  delete_after=15)

###################
#                 #
# CLEANUP         #
#                 #
###################

		# Cleanup Messages Command
	@commands.command(invoke_without_command=True, aliases=['clean', 'delete', 'del'])
	@checks.mod_or_permissions(manage_messages=True)
	async def cleanup(self, ctx, number: int = 1, *, user: discord.Member = None):
		"""Deletes last X messages [user]."""
		if ctx.message.channel.name in self.purge_ignore:
			return
		logging_channel = self.get_logging_channel(ctx.message)
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


###################
#                 #
# COGS            #
#                 #
###################

	@commands.command(hidden=True)
	@commands.is_owner()
	async def reload(self, ctx, *, ext):
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

	@commands.command(hidden=True)
	@commands.is_owner()
	async def load(self, ctx, *, ext):
		"""Load a cog."""
		if not ext.startswith('cogs.'):
			ext = f'cogs.{ext}'
		try:
			self.bot.load_extension(ext)
		except Exception as e:
			await ctx.send(f'`{e}`',  delete_after=60)
		else:
			await ctx.send(f'Cog {ext} loaded.',  delete_after=60)

	@commands.command(hidden=True)
	@commands.is_owner()
	async def unload(self, ctx, *, ext):
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
	@commands.command()
	@checks.admin_or_permissions(administrator=True)
	async def setplaying(self, ctx, *, status: str = '#PMA'):
		"""Sets the 'Playing' message for the bot."""
		await self.bot.change_presence(game=discord.Game(name=status))

		# Shows Uptime of the Server
	@commands.command()
	async def uptime(self, ctx):
		"""Shows the bots uptime"""
		up = abs(self.bot.uptime - int(time.perf_counter()))
		up = datetime.timedelta(seconds=up)
		await ctx.send(f'`Uptime: {up}`', delete_after=60)

	@commands.command(invoke_without_command=True, aliases=['user', 'uinfo', 'info', 'ui'])
	async def userinfo(self, ctx, *, name=""):
		"""Get user info. Ex: [p]info @user"""
		if name:
			try:
				user = ctx.message.mentions[0]
			except IndexError:
				user = ctx.guild.get_member_named(name)
			if not user:
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

		await ctx.message.delete()
		
def setup(bot):
	bot.add_cog(Utility(bot))
