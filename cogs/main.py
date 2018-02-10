import asyncio

import datetime
import time

from discord.ext import commands
import discord

from utils import checks

sellout_cooldown = 7200

###################
#                 #
# MAIN            #
#                 #
###################


class Main:
	def __init__(self, bot):
		self.bot = bot
		self.cooldowns = {}
		
	def check_cd(self, guild):
		if guild.id not in self.cooldowns:
			self.cooldowns[guild.id] = {}
		if guild.id in self.cooldowns[guild.id]:
			if time.time() - self.cooldowns[guild.id][guild.id] < sellout_cooldown:
				return False
		return True
		
###################
#                 #
# STATS           #
#                 #
###################

		# Server Stats Command
	@commands.group(invoke_without_command=True)
	async def stats(self, ctx):
		"""Lets you see various stats regarding the server."""
		thumbnail = ''
		text_channels, voice_channels = 0, 0
		for chan in ctx.guild.channels:
			if isinstance(chan, discord.TextChannel):
				text_channels += 1
			elif isinstance(chan, discord.VoiceChannel):
				voice_channels += 1
		title = f'**{ctx.guild.name}**'
		description = ctx.guild.created_at.strftime('Created on %B %d{} %Y')
		day = ctx.guild.created_at.day
		description = description.format("th" if 4 <= day % 100 <= 20 else
										{1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th"))
		footer = f'{ctx.invoked_with.title()} ID: {ctx.guild.id}'
		embed = discord.Embed(colour=discord.Colour(0xffffff), title=title, description=description)
		embed.set_thumbnail(url=thumbnail)
		embed.add_field(name='Region', value=ctx.guild.region)
		embed.add_field(name='Members', value=len(ctx.guild.members))
		embed.add_field(name='Text Channels', value=text_channels)
		embed.add_field(name='Voice Channels', value=voice_channels)
		embed.add_field(name='Roles', value=len(ctx.guild.roles))
		embed.add_field(name='Owner', value=ctx.guild.owner)
		embed.set_footer(text=footer)
		await ctx.send(embed=embed, delete_after=30)

###################
#                 #
# SELLOUT         #
#                 #
###################

#		# Server Twitch Sellout Command
#	@checks.db
#	@commands.command()
#	@commands.cooldown(1, 7200, commands.BucketType.guild)
#	@commands.guild_only()
#	async def sellout(self, ctx):
#		"""Sellout the server streamer and get points."""
#		if ctx.invoked_subcommand is None:
#			if self.check_cd(ctx.guild):
#				self.cooldowns[ctx.guild.id][ctx.author.id] = time.time()
#				async with ctx.con.transaction(isolation='serializable'):
#					reply = f'**{ctx.author.name}** has soldout the server! *+2 points!*'
#					await ctx.con.execute('''
#						INSERT INTO sellout (guild_id, user_id, total, current) VALUES
#						($1, $2, 1, 2) ON CONFLICT (guild_id, user_id) DO
#						UPDATE SET total = sellout.total + 1, current = sellout.current + 2
#						''', ctx.guild.id, ctx.author.id)
#					settings = await ctx.con.fetchrow('''
#						SELECT * FROM sellout WHERE guild_id = $1
#						''', ctx.guild.id)
#				await ctx.send(reply, delete_after=30)
#				await ctx.send(settings['message'].format(ctx.author, ctx.guild))
#
#		# Sets the Server Twitch Sellout Command
#	@checks.db
#	@checks.no_delete
#	@commands.command()
#	async def selloutset(self, ctx, *, format_msg = None):
#		"""Sets the sellout message for the server."""
#		if format_msg is None:
#			await self.bot.send_help(ctx)
#			return
#		async with ctx.con.transaction():
#			settings = await ctx.con.fetchrow('''
#				UPDATE sellout SET message = $1 WHERE guild_id = $2
#				''', format_msg, ctx.guild.id)
#		await ctx.send('Sellout message set for the server.', delete_after=15)
#		settings = await ctx.con.fetchrow('''
#			SELECT * FROM sellout WHERE guild_id = $1
#			''', ctx.guild.id)
#		await ctx.send(settings['message'].format(ctx.author, ctx.guild), delete_after=15)

###################
#                 #
# BALANCE/POINTS  #
#                 #
###################
		
		# Balance Command
	@checks.db
	@commands.command(name='balance', aliases=['bal', 'bank'])
	@commands.guild_only()
	async def points(self, ctx, user: discord.Member = None):
		"""See how many points you have."""
		if user is None:
			user = ctx.author
		row = await ctx.con.fetchrow('''
			SELECT total, current FROM sellout WHERE guild_id = $1 AND user_id = $2
			''', ctx.guild.id, user.id)
		if row is None:
			total, current = 0, 0
		else:
			total, current = row['total'], row['current']
		await ctx.send(f'**{user.name}**, you have helped this server **{total}** times, and have a balance of **{current}**.', delete_after=120)

		# Pay Points Command
	@checks.db
	@commands.command()
	@commands.guild_only()
	@checks.admin_or_permissions()
	async def pay(self, ctx, member: discord.Member, amount: int, total_add: int = 1):
		"""Allows admins to give people points."""
		await ctx.con.execute('''
			INSERT INTO sellout (guild_id, user_id, current, total)
			VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, user_id) DO
			UPDATE SET current = sellout.current + $3, total = sellout.total + $4
			''', ctx.guild.id, member.id, amount, total_add)
		await ctx.send(f'**{member.name}** has been given {amount} points.', delete_after=60)


def setup(bot):
	bot.add_cog(Main(bot))
