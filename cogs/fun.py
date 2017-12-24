import random
from random import randint
import time
import asyncpg
import asyncio

from discord.ext import commands
import discord

from utils import checks

MEMES = {
	"intellectual": "https://cdn.discordapp.com/attachments/383490727180500993/386383095554768896/unknown-2.png",
	"thottie": "H O T T I E L I K E A T H O T T I E"
}

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
		elif member is ctx.author:
			await ctx.send(f'**{member.name}... why tho?**')
			return
		await ctx.send(f'**{member.name}**, you got slapped by **{ctx.message.author.name}**! :rage::clap:')
		
		
	@checks.db
	@checks.no_delete
	@commands.command(aliases=['drink'])
	async def beer(self, ctx, *, member: discord.Member = None):
		"""Give someone a beer! 🍻 """
		if member is None:
			await ctx.send('Specify a user to give a beer',  delete_after=15)
			return
		elif member is ctx.author:
			await ctx.send(f'**{member.name}**, drinking alone is the way to go!! :beer:')
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
		elif member is ctx.author:
			await ctx.send(f'Who needs to share cookies?? Not **{member.name}**!!\n:cookie: Om Nom Nom Nom :cookie:')
			return
		await ctx.send(f'**{member.name}**, you got a :cookie: from **{ctx.message.author.name}**!')
			
	@checks.db
	@checks.no_delete
	@checks.is_owner()
	@commands.command()
	async def fuckboi(self, ctx, *, member: discord.Member = None):
		"""Call someone a fuckboi?"""
		if member is None:
			await ctx.send('Specify a user/member',  delete_after=15)
			return
		await ctx.send(f'**{member.name}**, why are you a fuckboi... :thinking:')
	
	@checks.db
	@checks.no_delete
	@checks.is_owner()
	@commands.command(aliases=['school'])
	async def education(self, ctx, *, member: discord.Member = None):
		"""Education >> thots & hoes"""
		if member is None:
			await ctx.send('Specify a user/member',  delete_after=15)
			return
		await ctx.send(f'**{member.name}**, your schooling and education are more important!! :school:')
		
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
	@commands.command(aliases=['doubt'])
	async def x(self, ctx):
		"""Press X to doubt"""
		em = discord.Embed(colour=discord.Colour(0x6666CC))
		em.set_author(name=str(ctx.message.author), icon_url=ctx.message.author.avatar_url)
		em.set_image(url='https://i.imgur.com/AbUWe1d.png')
		await ctx.send(f'**{ctx.message.author.name}** has pressed X to doubt', embed=em)
		
	@checks.db
	@checks.no_delete
	@commands.command()
	async def clap(self, ctx, *, member: discord.Member = None):
		"""Congratulate another person"""
		member = member or ctx.author

		await ctx.send(':sun_with_face::clap:')
		
		
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

	@checks.db
	@checks.no_delete
	async def meme(self, ctx, *, meme_str: str = 'list'):
		if meme_str == 'list':
			result = "Available memes: " + ', '.join(MEMES.keys())
		else:
			result = MEMES.get(meme_str, meme_str + " is not a meme")
		
		await ctx.send(result)

		
def setup(bot):
	bot.add_cog(Fun(bot))
