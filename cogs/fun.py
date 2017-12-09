import random
from random import randint
import time
import asyncpg
import asyncio

from discord.ext import commands
import discord

from utils import checks

fun_cooldown = 30

class Fun:
	def __init__(self, bot):
		self.bot = bot
		
###################
#                 #
# REACTIONS       #
#                 #
###################
	
	@checks.db
	@checks.no_delete
	@commands.command()
	async def slap(self, ctx, *, member: discord.Member = None):
		"""Slap another person"""
		if member is None:
			await ctx.send('Specify a user to slap',  delete_after=15)
			return
		await ctx.send(f'**{member.name}**, you got slapped by **{ctx.message.author.name}**!')
		
		
	@checks.db
	@checks.no_delete
	@commands.command(aliases=['drink'])
	async def beer(self, ctx, *, member: discord.Member = None):
		"""Give someone a beer! 🍻 """
		if member is None:
			await ctx.send('Specify a user to give a beer',  delete_after=15)
			return
		await ctx.send(f'**{member.name}**, you got a :beer: from **{ctx.message.author.name}**!')
		
		
	@checks.db
	@checks.no_delete
	@commands.command()
	async def cookie(self, ctx, *, member: discord.Member = None):
		"""Give someone a cookie! 🍪 """
		if member is None:
			await ctx.send('Specify a user to give a cookie',  delete_after=15)
			return
		await ctx.send(f'**{member.name}**, you got a :cookie: from **{ctx.message.author.name}**!')
		
	@checks.db
	@checks.no_delete
	@commands.command()
	async def clap(self, ctx, *, member: discord.Member = None):
		"""Congratulate another person"""
		if member is None:
			await ctx.send('Specify a user/member',  delete_after=15)
			return
		await ctx.send(f'**{member.name}**, congrats! :sun_with_face::clap:')
	
	@checks.db
	@checks.no_delete
	@checks.is_owner()
	@commands.command()
	async def fuckboi(self, ctx, *, member: discord.Member = None):
		"""Who's a fuckboi?"""
		if member is None:
			await ctx.send('Specify a user/member',  delete_after=15)
			return
		await ctx.send(f'**{member.name}**, why are you a fuckboi... :thinking:')
		
###################
#                 #
# RANDOM          #
#                 #
###################
		
	@checks.db
	@checks.no_delete
	@commands.command(aliases=['respect'])
	async def f(self, ctx):
		"""Press F to pay respects"""
		hearts = [':heart:', ':sparkling_heart:', ':green_heart:', ':purple_heart:', ':yellow_heart:', ':blue_heart:', ':black_heart: ']
		await ctx.send(f'**{ctx.message.author.name}** has paid their respects {random.choice(hearts)}')
		
	@checks.db
	@checks.no_delete
	@commands.command(aliases=['dice'])
	async def roll(self, ctx, *, high: str='6'):
		"""Rolls a number between the given range"""
		if not high.isdigit():
			high = 6
			return
		roll = randint(1, int(high))
		await ctx.send(f'**{ctx.message.author.name}**, you rolled a {high}-sided :game_die: and got **{roll}**!')
	
	
	
def setup(bot):
	bot.add_cog(Fun(bot))
