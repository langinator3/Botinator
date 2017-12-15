import datetime
import asyncio
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
		self.log_ignore = ['pokemon', 'role-assigning']
		self.attachment_cache = {}

	def __unload(self):
		self.purge_task.cancel()

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
		if message.author.bot:
			return
		if message.channel.id == logging_channel.id:
			em = discord.Embed.from_data(message.embeds[0])
			await logging_channel.send('Ping')
			await logging_channel.send('Someone deleted this!', embed=em)
			return
		if not message.content and message.attachments:
			content = 'Attachments:'
			content += '\n'.join('{0.filename} {0.url}'.format(attach) for attach in message.attachments)
		else:
			content = message.content
		description = f'{message.channel.mention}\n{content}'
		em = discord.Embed(colour=discord.Colour.red(), description='**[MESSAGE DELETED]**\n' + description)
		em.set_author(name=str(message.author), icon_url=message.author.avatar_url)
		em.timestamp = datetime.datetime.utcnow()
		await logging_channel.send(embed=em)

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
	@commands.command()
	@commands.is_owner()
	async def plonk(self, ctx, user: discord.Member):
		"""Adds a user to the bot's blacklist"""
		try:
			async with ctx.con.transaction():
				await ctx.con.execute('''
					INSERT INTO plonks (guild_id, user_id) VALUES ($1, $2)
					''', ctx.guild.id, user.id)
		except asyncpg.UniqueViolationError:
			await ctx.send('User is already plonked.',  delete_after=60)
		else:
			await ctx.send('User has been plonked.',  delete_after=60)

		# Unblacklist Command
	@checks.db
	@commands.command()
	@commands.is_owner()
	async def unplonk(self, ctx, user: discord.Member):
		"""Removes a user from the bot's blacklist"""
		async with ctx.con.transaction():
			res = await ctx.con.execute('''
				DELETE FROM plonks WHERE guild_id = $1 and user_id = $2
				''', ctx.guild.id, user.id)
		deleted = int(res.split()[-1])
		if deleted:
			await ctx.send('User is no longer plonked.',  delete_after=60)
		else:
			await ctx.send('User is not plonked.',  delete_after=60)

###################
#                 #
# CLEANUP         #
#                 #
###################

		# Cleanup Messages Command
	@commands.command(invoke_without_command=True, aliases=['clean', 'delete', 'del'])
	@checks.mod_or_permissions(manage_messages=True)
	async def cleanup(self, ctx, number: int = None, *, user: discord.Member = None):
		"""Deletes last X messages (user)."""
		logging_channel = self.get_logging_channel(ctx.message)
		if number is None:
			await ctx.send('Specify a number of messages to remove.',  delete_after=30)
			return
		if number < 1:
			number = 1
		elif isinstance(user, discord.Member):
			def is_user(m):
				return m.id == ctx.message.id or m.author == user
			try:
				await ctx.channel.purge(limit=number + 1, check=is_user)
				em = discord.Embed(colour=discord.Colour(0x6666CC))
				em.description = "{0.name}({0.id}) deleted {1} messages made by {2.name}({2.id}) in channel {3}".format(ctx.author, number, user, ctx.channel.mention)
				em.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
				em.timestamp = datetime.datetime.utcnow()
				await logging_channel.send(embed=em)
				return
			except discord.errors.Forbidden:
				await ctx.send('I need permissions to manage messages in this channel.',  delete_after=120)
				return
		elif isinstance(number, int):
			try:
				await ctx.channel.purge(limit=number + 1, check=pin_check)
				em = discord.Embed(colour=discord.Colour(0x6666CC))
				em.description = "{}({}) deleted {} messages in channel {}".format(ctx.author.name, ctx.author.id, number, ctx.channel.mention)
				em.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
				em.timestamp = datetime.datetime.utcnow()
				await logging_channel.send(embed=em)
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
	async def setplaying(self, ctx, *, status: str):
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
		await ctx.send(embed=em)

		await ctx.message.delete()
		
def setup(bot):
	bot.add_cog(Utility(bot))
