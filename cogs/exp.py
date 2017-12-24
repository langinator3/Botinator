from random import randint
import time
import asyncpg
import asyncio

from discord.ext import commands
import discord

from cogs.menus import Menus, ARROWS, CANCEL
from utils import checks

exp_cooldown = 60
exp_min_amount = 15
exp_max_amount = 25
# exp_min_amount = 30 #Double EXP
# exp_max_amount = 50 #Double EXP


def level_req(level):
	return round(6*(level**2)+50*level+100)


def total_level(to):
	return sum(level_req(level) for level in range(1, to + 1))


def clean_name(name):
	return name.replace("`", "\\`").replace("@", "@" + u'\u200b')


class Exp(Menus):
	def __init__(self, bot):
		self.bot = bot
		self.cooldowns = {}

	def check_cd(self, member):
		if member.guild.id not in self.cooldowns:
			self.cooldowns[member.guild.id] = {}
		if member.id in self.cooldowns[member.guild.id]:
			if time.time() - self.cooldowns[member.guild.id][member.id] < exp_cooldown:
				return False
		return True

###################
#                 #
# ON_MESSAGE      #
#                 #
###################

		# Experience for being active
		# Updates both Global and Guild XP
	async def on_message(self, message):
		if message.author.bot or await self.bot.is_command(message):
			return
		if self.check_cd(message.author):
			prestiged = False
			leveled = False
			add_exp = randint(exp_min_amount, exp_max_amount)
			async with self.bot.db_pool.acquire() as con:
				for wait in range(3):  # try updating XP 3 times.
					try:
						async with con.transaction(isolation='serializable'):
							rec = await con.fetchrow('''
								SELECT exp, total, level, prestige FROM experience WHERE user_id = $1 AND guild_id = $2
								''', message.author.id, message.guild.id) or {'exp': 0, 'total': 0, 'level': 0, 'prestige': 0}
							g_rec = await con.fetchrow('''
								SELECT exp, total, level, prestige FROM g_experience WHERE user_id = $1
								''', message.author.id) or {'exp': 0, 'total': 0, 'level': 0, 'prestige': 0}
							self.cooldowns[message.guild.id][message.author.id] = time.time()
							g_add_exp = add_exp
							g_exp = g_rec['exp'] + g_add_exp
							g_total = g_rec['total'] + g_add_exp
							g_level = g_rec['level']
							g_prestige = g_rec['prestige']
							g_to_next_level = level_req(g_level + 1)
							while g_exp >= g_to_next_level:
								g_exp -= g_to_next_level
								g_level += 1
								if g_level == 30:
									g_level = 0
									g_prestige += 1
							x_rec = await con.fetchrow('''
								SELECT xp_mult FROM event WHERE guild_id = $1
								''', message.guild.id) or {'xp_mult': 1}
							l_add_exp = add_exp * x_rec['xp_mult']
							exp = rec['exp'] + l_add_exp
							total = rec['total'] + l_add_exp
							level = rec['level']
							prestige = rec['prestige']
							to_next_level = level_req(level + 1)
							while exp >= to_next_level:
								exp -= to_next_level
								level += 1
								if level == 30:
									level = 0
									prestige += 1
									prestiged = True
								else:
									leveled = True
							await con.execute('''
								INSERT INTO experience (guild_id, user_id, exp, total, level, prestige) VALUES ($1, $2, $3, $4, $5, $6)
								ON CONFLICT (guild_id, user_id) DO
								UPDATE SET exp = $3, total = $4, level = $5, prestige = $6
								''', message.guild.id, message.author.id, exp, total, level, prestige)
							await con.execute('''
								INSERT INTO g_experience (user_id, exp, total, level, prestige) VALUES ($1, $2, $3, $4, $5)
								ON CONFLICT (user_id) DO
								UPDATE SET exp = $2, total = $3, level = $4, prestige = $5
								''', message.author.id, g_exp, g_total, g_level, g_prestige)
					except asyncpg.SerializationError:
						prestiged = False  # in case fails 3 times
						leveled = False
						await asyncio.sleep(wait)
						continue
					else:
						break
			if prestiged:
				await message.channel.send(f'**{message.author.name}** has prestiged and is now prestige level **{prestige}**!', delete_after=120)
			elif leveled:
				await message.channel.send(f'**{message.author.name}** has reached level **{level}**!', delete_after=120)
		

###################
#                 #
# LEVEL           #
#                 #
###################

		# Shows your Guild level
	@checks.db
	@checks.no_delete
	@commands.command(name='level', aliases=['lvl', 'experience', 'exp', 'xp', 'prestige'])
	@commands.guild_only()
	async def experience(self, ctx, name=""):
		"""Shows yours or another person's level."""
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

		rec = await ctx.con.fetchrow('''
			SELECT exp, total, level, prestige FROM experience WHERE user_id = $1 AND guild_id = $2
			''', user.id, ctx.guild.id) or {'exp': 0, 'total': 0, 'level': 0, 'prestige': 0}
		exp, total, level, prestige = rec['exp'], rec['total'], rec['level'], rec['prestige']
		to_next_level = level_req(level + 1)
		thumbnail = f'http://pokebot.xyz/static/img/prestige/P{prestige}.png'
		embed = discord.Embed(colour=0xffffff)
		embed.set_author(name=user.name, icon_url=user.avatar_url)
		embed.set_thumbnail(url=thumbnail)
		embed.add_field(name='LEVEL', value=level)
		embed.add_field(name='EXP', value=f'{exp}/{to_next_level} (tot. {total})')
		await ctx.send(embed=embed, delete_after=60)

###################
#                 #
# RANK            #
#                 #
###################

		# Shows the Guild's EXP ranks
	@checks.db
	@commands.command(name='leaderboard', aliases=['ranking', 'rank', 'lb', 'ranks'])
	@commands.guild_only()
	async def rank(self, ctx):
		"""Shows the EXP leaderboard."""
		ordered = await ctx.con.fetch('''
			SELECT * FROM experience WHERE guild_id = $1 ORDER BY total DESC
			''', ctx.guild.id)
		options = [[{'name': 'Rank', 'value': ''}, {'name': 'User', 'value': ''}, {'name': 'Exp.', 'value': ''}]]
		on_cur_page = 0
		ind = 1
		for total in ordered:
			if on_cur_page == 10:
				options.append([{'name': 'Rank', 'value': ''}, {'name': 'User', 'value': ''}, {'name': 'Exp.', 'value': ''}])
				on_cur_page = 0
			member = ctx.guild.get_member(total['user_id'])
			if member is None:
				continue
			rec = await ctx.con.fetchrow('''
				SELECT exp, total, level, prestige FROM experience WHERE user_id = $1 AND guild_id = $2
				''', member.id, ctx.guild.id) or {'exp': 0, 'total': 0, 'level': 0, 'prestige': 0}
			exp, total, level, prestige = rec['exp'], rec['total'], rec['level'], rec['prestige']
			to_next_level = level_req(level + 1)
			if options[-1][0]['value']:
				options[-1][0]['value'] += '\n'
			options[-1][0]['value'] += f'#{ind}'
			if options[-1][1]['value']:
				options[-1][1]['value'] += '\n'
			options[-1][1]['value'] += member.name
			if options[-1][2]['value']:
				options[-1][2]['value'] += '\n'
			options[-1][2]['value'] += f'Prestige. {prestige}.{level} (Exp. {total})'
			ind += 1
			on_cur_page += 1
		title = '**Leaderboard**'
		description = f'{ARROWS[0]} Click to go back a page.\n{ARROWS[1]} Click to go forward a page.\n{CANCEL} Click to exit the list.'
		await self.embed_reaction_menu(options, ctx.author, ctx.channel, 0, timeout=120, title=title, description=description)

###################
#                 #
# GLOBAL LEVEL    #
#                 #
###################

		# Shows your Global level
	@checks.db
	@checks.no_delete
	@commands.command(name='globallevel', aliases=['glvl', 'glevel', 'gexperience', 'gexp', 'gxp', 'gprestige'])
	async def gexperience(self, ctx, name=""):
		"""Shows yours or another person's Global level."""
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

		rec = await ctx.con.fetchrow('''
			SELECT exp, total, level, prestige FROM g_experience WHERE user_id = $1
			''', user.id) or {'exp': 0, 'total': 0, 'level': 0, 'prestige': 0}
		exp, total, level, prestige = rec['exp'], rec['total'], rec['level'], rec['prestige']
		to_next_level = level_req(level + 1)
		thumbnail = f'http://pokebot.xyz/static/img/prestige/P{prestige}.png'
		embed = discord.Embed(colour=0xffffff)
		embed.set_author(name=user.name, icon_url=user.avatar_url)
		embed.set_thumbnail(url=thumbnail)
		embed.add_field(name='GLOBAL LEVEL', value=level)
		embed.add_field(name='GLOBAL EXP', value=f'{exp}/{to_next_level} (tot. {total})')
		await ctx.send(embed=embed, delete_after=120)

###################
#                 #
# GLOBAL RANK     #
#                 #
###################

		# Shows the Guild's EXP ranks
	@checks.db
	@commands.command(name='globalrank', aliases=['grank', 'granking', 'gleaderboard', 'glb', 'granks'])
	async def grank(self, ctx):
		"""Shows the Global EXP leaderboard."""
		ordered = await ctx.con.fetch('''
			SELECT * FROM g_experience ORDER BY total DESC
			''')
		options = [[{'name': 'Global Rank', 'value': ''}, {'name': 'User', 'value': ''}, {'name': 'Exp.', 'value': ''}]]
		on_cur_page = 0
		ind = 1
		for total in ordered:
			if on_cur_page == 10:
				options.append([{'name': 'Global Rank', 'value': ''}, {'name': 'User', 'value': ''}, {'name': 'Exp.', 'value': ''}])
				on_cur_page = 0
			member = ctx.guild.get_member(total['user_id'])
			if member is None:
				continue
			rec = await ctx.con.fetchrow('''
				SELECT exp, total, level, prestige FROM g_experience WHERE user_id = $1
				''', member.id) or {'exp': 0, 'total': 0, 'level': 0, 'prestige': 0}
			exp, total, level, prestige = rec['exp'], rec['total'], rec['level'], rec['prestige']
			to_next_level = level_req(level + 1)
			if options[-1][0]['value']:
				options[-1][0]['value'] += '\n'
			options[-1][0]['value'] += f'#{ind}'
			if options[-1][1]['value']:
				options[-1][1]['value'] += '\n'
			options[-1][1]['value'] += member.name
			if options[-1][2]['value']:
				options[-1][2]['value'] += '\n'
			options[-1][2]['value'] += f'Lvl. {prestige}.{level} (Exp. {total})'
			ind += 1
			on_cur_page += 1
		title = '**Global Leaderboard**'
		description = f'{ARROWS[0]} Click to go back a page.\n{ARROWS[1]} Click to go forward a page.\n{CANCEL} Click to exit the list.'
		await self.embed_reaction_menu(options, ctx.author, ctx.channel, 0, timeout=120, title=title, description=description)

###################
#                 #
# XP MULTIPLIER   #
#                 #
###################

		# Sets Guild XP Multiplier
	@checks.db
	@commands.command()
	@commands.guild_only()
	@checks.admin_or_permissions()
	async def setmult(self, ctx, mult: str = None):
		"""Allows admins to change XP multiplier."""
		if not mult.isdigit():
			await ctx.send('Specify positive multiplier to set',  delete_after=15)
			return
		set_mult = int(mult)
		async with ctx.con.transaction():
			settings = await ctx.con.execute('''
			INSERT INTO event (guild_id, xp_mult) VALUES ($1, $2)
			ON CONFLICT (guild_id) DO
			UPDATE SET xp_mult = $2
			''', ctx.guild.id, set_mult)
		await ctx.send(f'Experience multiplier has been set to **{set_mult}** for this server', delete_after=120)

###################
#                 #
# GIVEXP          #
#                 #
###################

		# Gives players experience, levels, prestiges
	@checks.db
	@commands.command(hidden=True)
	@commands.guild_only()
	@checks.admin_or_permissions()
	async def givexp(self, ctx, member: discord.Member = None, add_exp: str = None):
		"""Allows admins to give people XP."""
		if member is None:
			await ctx.send('Specify a user to award experience',  delete_after=15)
			return
		if not add_exp.isdigit():
			await ctx.send('Specify an amount of experience to GIVE',  delete_after=15)
			return
		async with self.bot.db_pool.acquire() as con:
			for wait in range(3):  # try updating XP 3 times.
				try:
					async with con.transaction(isolation='serializable'):
						rec = await ctx.con.fetchrow('''
							SELECT exp, total, level, prestige FROM experience WHERE user_id = $1 AND guild_id = $2
							''', member.id, ctx.guild.id) or {'exp': 0, 'total': 0, 'level': 0, 'prestige': 0}
						exp = rec['exp'] + int(add_exp)
						total = rec['total'] + int(add_exp)
						level = rec['level']
						prestige = rec['prestige']
						to_next_level = level_req(level + 1)
						while exp >= to_next_level:
							level += 1
							exp -= to_next_level
							to_next_level = level_req(level + 1)
							if level == 30:
								level = 0
								prestige += 1
								prestiged = True
							else:
								leveled = True
						await con.execute('''
							INSERT INTO experience (guild_id, user_id, exp, total, level, prestige) VALUES ($1, $2, $3, $4, $5, $6)
							ON CONFLICT (guild_id, user_id) DO
							UPDATE SET exp = $3, total = $4, level = $5, prestige = $6
							''', ctx.guild.id, member.id, exp, total, level, prestige)
						await ctx.send(f'**{member.name}** has been given {add_exp} Experience.', delete_after=120)
				except asyncpg.SerializationError:
					prestiged = False  # in case fails 3 times
					leveled = False
					await asyncio.sleep(wait)
					continue
				else:
					break

###################
#                 #
# SETXP           #
#                 #
###################

		# Sets players experience, levels, prestiges
	@checks.db
	@commands.command(hidden=True)
	@commands.guild_only()
	@checks.admin_or_permissions()
	async def setxp(self, ctx, member: discord.Member = None, set_total: str = None):
		"""Allows admins to set people's XP."""
		if member is None:
			await ctx.send('Specify a user to award experience',  delete_after=15)
			return
		if not set_total.isdigit():
			await ctx.send('Specify positive an amount of experience to set',  delete_after=15)
			return
		async with self.bot.db_pool.acquire() as con:
			for wait in range(3):  # try updating XP 3 times.
				try:
					async with con.transaction(isolation='serializable'):				
						exp = total = int(set_total)
						level = prestige = 0
						to_next_level = level_req(level + 1)
						while exp >= to_next_level:
							level += 1
							exp -= to_next_level
							to_next_level = level_req(level + 1)
							if level == 30:
								level = 0
								prestige += 1
								prestiged = True
							else:
								leveled = True
						await con.execute('''
							INSERT INTO experience (guild_id, user_id, exp, total, level, prestige) VALUES ($1, $2, $3, $4, $5, $6)
							ON CONFLICT (guild_id, user_id) DO
							UPDATE SET exp = $3, total = $4, level = $5, prestige = $6
							''', ctx.guild.id, member.id, exp, total, level, prestige)
						await ctx.send(f'**{member.name}**\'s Experience has been set to {set_total}.', delete_after=120)
				except asyncpg.SerializationError:
					prestiged = False  # in case fails 3 times
					leveled = False
					await asyncio.sleep(wait)
					continue
				else:
					break

###################
#                 #
# GLOBAL GIVEXP   #
#                 #
###################

		# Gives players Global experience, levels, prestiges
	@checks.db
	@commands.command(hidden=True)
	@commands.is_owner()
	async def ggivexp(self, ctx, member: discord.Member = None, add_exp: str = None):
		"""Allows the owner to give people Global XP."""
		if member is None:
			await ctx.send('Specify a user to award experience',  delete_after=15)
			return
		if not add_exp.isdigit():
			await ctx.send('Specify an amount of experience to GIVE',  delete_after=15)
			return
		async with self.bot.db_pool.acquire() as con:
			for wait in range(3):  # try updating XP 3 times.
				try:
					async with con.transaction(isolation='serializable'):
						rec = await ctx.con.fetchrow('''
							SELECT exp, total, level, prestige FROM g_experience WHERE user_id = $1
							''', member.id) or {'exp': 0, 'total': 0, 'level': 0, 'prestige': 0}
						exp = rec['exp'] + int(add_exp)
						total = rec['total'] + int(add_exp)
						level = rec['level']
						prestige = rec['prestige']
						to_next_level = level_req(level + 1)
						while exp >= to_next_level:
							level += 1
							exp -= to_next_level
							to_next_level = level_req(level + 1)
							if level == 30:
								level = 0
								prestige += 1
								prestiged = True
							else:
								leveled = True
						await con.execute('''
							INSERT INTO g_experience (user_id, exp, total, level, prestige) VALUES ($1, $2, $3, $4, $5)
							ON CONFLICT (user_id) DO
							UPDATE SET exp = $2, total = $3, level = $4, prestige = $5
							''', member.id, exp, total, level, prestige)
						await ctx.send(f'**{member.name}** has been given {add_exp} Global Experience.', delete_after=120)
				except asyncpg.SerializationError:
					prestiged = False  # in case fails 3 times
					leveled = False
					await asyncio.sleep(wait)
					continue
				else:
					break

###################
#                 #
# GLOBAL SETXP    #
#                 #
###################

		# Sets players Global experience, levels, prestiges
	@checks.db
	@commands.command(hidden=True)
	@commands.is_owner()
	async def gsetxp(self, ctx, member: discord.Member = None, set_total: str = None):
		"""Allows owner to set people's Global XP."""
		if member is None:
			await ctx.send('Specify a user to award experience',  delete_after=15)
			return
		if not set_total.isdigit():
			await ctx.send('Specify positive an amount of experience to set',  delete_after=15)
			return
		async with self.bot.db_pool.acquire() as con:
			for wait in range(3):  # try updating XP 3 times.
				try:
					async with con.transaction(isolation='serializable'):				
						exp = total = int(set_total)
						level = prestige = 0
						to_next_level = level_req(level + 1)
						while exp >= to_next_level:
							level += 1
							exp -= to_next_level
							to_next_level = level_req(level + 1)
							if level == 30:
								level = 0
								prestige += 1
								prestiged = True
							else:
								leveled = True
						await con.execute('''
							INSERT INTO g_experience (user_id, exp, total, level, prestige) VALUES ($1, $2, $3, $4, $5)
							ON CONFLICT (user_id) DO
							UPDATE SET exp = $2, total = $3, level = $4, prestige = $5
							''', member.id, exp, total, level, prestige)
						await ctx.send(f'**{member.name}**\'s Global Experience has been set to {set_total}.', delete_after=120)
				except asyncpg.SerializationError:
					prestiged = False  # in case fails 3 times
					leveled = False
					await asyncio.sleep(wait)
					continue
				else:
					break

def setup(bot):
	bot.add_cog(Exp(bot))
