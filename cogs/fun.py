import random
from random import randint
import time
import asyncpg
import asyncio
import aiohttp

from discord.ext import commands
import discord

from utils import checks

MEMES = {
	"intellectual": "https://cdn.discordapp.com/attachments/386029171303776257/386379713431470081/unknown-2.png",
	"bestdad": "https://cdn.discordapp.com/attachments/386029171303776257/386382834782306306/Screen_Shot_2017-12-01_at_9.07.06_PM.png",
	"thottie": "H O T T I E L I K E A T H O T T I E",
	"scary": "https://cdn.discordapp.com/attachments/290366425116180481/410639882004856832/unknown.png",
	"rough": "https://cdn.discordapp.com/attachments/383755883617714188/398222122197188618/X5tD7M5.gif",
	"noice": "https://cdn.discordapp.com/attachments/383755883617714188/398222846394105856/giphy.gif"
}

EZ = [
	'Ah shucks... you guys are the best!',
	'C\'mon, Mom! One more game before you tuck me in. Oops mistell.',
	'For glory and honor! Huzzah comrades!',
	'Gee whiz! That was fun. Good playing!',
	'Good game! Best of luck to you all!',
	'Great game, everyone!',
	'I could really use a hug right now.',
	'I feel very, very small... please hold me...',
	'I\'m trying to be a nicer person. It\'s hard, but I am trying guys.',
	'I\'m wrestling with some insecurity issues in my life but thank you all for playing with me.',
	'It was an honor to play with you all. Thank you.',
	'It\'s past my bedtime. Please don’t tell my mommy.',
	'Mommy says people my age shouldn’t suck their thumbs.',
	'Well played. I salute you all.',
	'Wishing you all the best.'
]

class Fun:
	def __init__(self, bot):
		self.bot = bot

	async def em(self, content, image, author):
		em = discord.Embed(colour=discord.Colour(0x6666CC), description=content)
		if image is not None:
			em.set_image(url=image)
		em.set_author(name=str(author), icon_url=author.avatar_url)
		return em

###################
#                 #
# MEMES           #
#                 #
###################

	async def on_message(self, message):
		if message.author.id == self.bot.user.id:
			return
		if message.content.startswith(self.bot.command_prefix):
			meme_str = message.content[1:]
			await message.delete()
		if meme_str == 'list':
			result = "Available memes: " + ', '.join(MEMES.keys())
		else:
			return
		em = discord.Embed(colour=discord.Colour(0x6666CC))
		em.set_author(name=str(message.author), icon_url=message.author.avatar_url)
		try:
			em.set_image(url=result)
			await message.channel.send('', embed=em, delete_after=30)
		except:
			await message.channel.send(result, delete_after=30)


###################
#                 #
# MEANTION        #
#                 #
###################

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

	@commands.command()
	async def fuckboi(self, ctx, *, member: discord.Member = None):
		"""Call someone a fuckboi?"""
		if member is None:
			await ctx.send('Why are you a fuckboi... :thinking:')
			return
		await ctx.send(f'**{member.name}**, why are you a fuckboi... :thinking:')

	@commands.command(aliases=['school'])
	async def education(self, ctx, *, member: discord.Member = None):
		"""Education >> thots & hoes"""
		if member is None:
			await ctx.send('Specify a user/member',  delete_after=15)
			return
		await ctx.send(f'**{member.name}**, your schooling and education are more important!! :school:')
	
	@commands.command(name='drug', aliases=['drugs'])
	async def no_drug(self, ctx, *, member: discord.Member = None):
		"""No drugs"""
		if member is None:
			await ctx.send('Specify a user/member',  delete_after=15)
			return
		await ctx.send(f'**{member.name}**... Do pugs, not drugs!! :dog:')
		
###################
#                 #
# RANDOM          #
#                 #
###################

	@commands.command(aliases=['respect'])
	async def f(self, ctx):
		"""Press F to pay respects"""
		hearts = [':heart:', ':sparkling_heart:', ':green_heart:', ':purple_heart:', ':yellow_heart:', ':blue_heart:', ':black_heart:']
		await ctx.send(f'**{ctx.message.author.nick if ctx.message.author.nick != None else ctx.message.author.name}** has paid their respects {random.choice(hearts)}')

	@commands.command(aliases=['doubt'])
	async def x(self, ctx):
		"""Press X to doubt"""
		await ctx.send(embed=await self.em('', 'https://i.imgur.com/AbUWe1d.png', ctx.author))

	@commands.command(name='ggez', aliases=['ezclap'])
	async def gg_ez(self, ctx):
		"""Good game, too easy"""
		await ctx.send(embed=await self.em('{}'.format(random.choice(EZ)), '', ctx.author))

	@checks.no_delete
	@commands.command()
	async def clap(self, ctx):
		"""Clap"""
		await ctx.send(':sun_with_face::clap:')

	@commands.command(aliases=['dice'])
	async def roll(self, ctx, *, high: str='6'):
		"""Rolls a number between the given range"""
		if not high.isdigit():
			high = 6
			return
		roll = randint(1, int(high))
		await ctx.send(f'**{ctx.message.author.name}**, you rolled a {high}-sided :game_die: and got **{roll}**!')

	@commands.command()
	async def love(self, ctx):
		"""What is love?"""
		action = random.choice([ctx.send('https://www.youtube.com/watch?v=HEXWRTEbj1I'), ctx.invoke(self.g, query='define: love')])

		await action

	@commands.command(hidden=True)
	async def bored(self, ctx):
		"""boredom looms"""
		await ctx.send('http://i.imgur.com/BuTKSzf.png')

	@checks.mod()
	@commands.command(aliases=['mention', 'call'])
	async def spam(self, ctx, *, name=""):
		"""Don't let your memes be dreams"""
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
			return
		
		Spam = ['Going once!','Going twice!','Going three times!','Sold!! :moneybag::clap:']
		for x in range(0,4):
			await ctx.send(f"{user.mention} Hello? {Spam[x]}")
			await asyncio.sleep(5)
		
def setup(bot):
	bot.add_cog(Fun(bot))
