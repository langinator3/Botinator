from fuzzywuzzy import process
from random import randint
import itertools
import asyncpg
import asyncio

from discord.ext import commands
import aiohttp
import discord

from cogs.menus import Menus, STAR, GLOWING_STAR, SPARKLES, SPACER, ARROWS, DONE, CANCEL
from utils.utils import wrap, unique
from utils import errors, checks


converter = commands.MemberConverter()


pokeballs = ('Pokeball', 'Greatball', 'Ultraball', 'Masterball')


def pokechannel():
	def check(ctx):
		if ctx.channel.name in ['pokemon']:
			return True
		raise errors.WrongChannel(discord.utils.get(ctx.guild.channels, name='pokemon'))
	return commands.check(check)


def xp_to_level(level):
	return (level ** 3) // 2


def level_from_xp(xp):
	return int((xp * 2) ** (1 / 3))


def catch(mon, ball):
	r = randint(0, 99)
	legendary = mon['legendary']
	mythical = mon['mythical']
	if (ball == 0 and r < (15 if mythical else 25 if legendary else 50)) \
			or (ball == 1 and r < (25 if mythical else 35 if legendary else 75)) \
			or (ball == 2 and r < (35 if mythical else 50 if legendary else 90)) \
			or (ball == 3 and r < (65 if mythical else 90 if legendary else 100)):
		return True
	return False


async def poke_converter(ctx, user_or_num):
	if user_or_num is None:
		return None
	try:
		return await converter.convert(ctx, user_or_num)
	except commands.BadArgument:
		try:
			return int(user_or_num)
		except ValueError:
			return user_or_num


def is_shiny(trainer: asyncpg.Record, personality: int):
	b = bin(personality)[2:].zfill(32)
	upper, lower = int(b[:16], 2), int(b[16:], 2)
	shiny = (((trainer['user_id'] % 65536) ^ trainer['secret_id']) ^ (upper ^ lower)) <= (65536 / 400)
	return SPARKLES if shiny else ''


def get_star(mon: asyncpg.Record):
	return GLOWING_STAR if mon['mythical'] else STAR if mon['legendary'] else ''


def get_name(mon: asyncpg.Record):
	"""mon argument must have:
		name      : custom name
		base_name : pokemon's name
		form      : form name

	   Returns:
	   Speed Deoxys
	   Sonic (Speed Deoxys)
	"""
	if mon['form'] is not None:
		name = f"{mon['form']} {mon['base_name']}"
	else:
		name = mon['base_name']
	if mon['name']:
		name = f"{mon['name']} ({name})"
	return name


async def get_pokemon_color(ctx, num=0, *, mon: asyncpg.Record=None):
	if num:
		mon = await ctx.con.fetch('''
			SELECT type FROM pokemon WHERE num = $1 AND form_id = 0
			''', num)
	if mon is not None:
		colors = await ctx.con.fetch('''
			SELECT color FROM types WHERE name = ANY($1)''', mon['type'])
		return round(sum(color['color'] for color in colors) / len(colors))
	return 0


async def set_inventory(ctx, uid, inv):
	return await ctx.con.execute('''
		UPDATE trainers SET inventory = $1 WHERE user_id = $2
		''', inv, uid)


async def get_found_counts(ctx, uid):
	return await ctx.con.fetch('''
		SELECT num, form_id, COUNT(*) AS count,
		(SELECT name || (CASE WHEN mythical THEN '$2' WHEN legendary THEN '$3' ELSE '' END) FROM pokemon WHERE pokemon.num = found.num LIMIT 1),
		(SELECT form FROM pokemon WHERE pokemon.num = found.num AND pokemon.form_id = found.form_id)
		FROM found WHERE owner = $1 GROUP BY num, form_id ORDER BY num, form_id
		''', uid, GLOWING_STAR, STAR)


async def see(ctx, uid, num):
	"""num can be int or list"""
	if isinstance(num, int):
		await ctx.con.execute("""
					  INSERT INTO seen (user_id, num) VALUES ($1, $2)
					  ON CONFLICT DO NOTHING
					  """, uid, num)
	else:
		await ctx.con.executemany("""
					  INSERT INTO seen (user_id, num) VALUES ($1, $2)
					  ON CONFLICT DO NOTHING
					  """, [(uid, n) for n in num])


async def get_rewards(ctx):
	return await ctx.con.fetch('''
		SELECT * FROM rewards
		''')


async def get_evolution_chain(ctx, num):
	chain = [await ctx.con.fetchrow('''
		SELECT prev, next,
		(SELECT name || (CASE WHEN mythical THEN $2 WHEN legendary THEN $3 ELSE '' END) FROM pokemon p WHERE p.num = e.num LIMIT 1) AS name
		FROM evolutions e WHERE num = $1
		''', num, GLOWING_STAR, STAR)]
	cur_ind = 0
	if chain[0]['prev'] is not None:
		chain.insert(0, await ctx.con.fetchrow('''
			SELECT prev,
			(SELECT name || (CASE WHEN mythical THEN $2 WHEN legendary THEN $3 ELSE '' END) FROM pokemon p WHERE p.num = e.num LIMIT 1) AS name
			FROM evolutions e WHERE next = $1
			''', num, GLOWING_STAR, STAR))
		cur_ind += 1
		if chain[0]['prev'] is not None:
			chain.insert(0, await ctx.con.fetchrow('''
				SELECT name || (CASE WHEN mythical THEN $2 WHEN legendary THEN $3 ELSE '' END) AS name FROM pokemon WHERE num = $1 LIMIT 1
				''', chain[0]['prev'], GLOWING_STAR, STAR))
			cur_ind += 1
	if chain[-1]['next'] is not None:
		chain.extend(await ctx.con.fetch('''
			SELECT
			(SELECT name || (CASE WHEN mythical THEN $2 WHEN legendary THEN $3 ELSE '' END) FROM pokemon p WHERE p.num = e.num LIMIT 1) AS name,
			(SELECT ARRAY(SELECT (SELECT name || (CASE WHEN mythical THEN $2 WHEN legendary THEN $3 ELSE '' END) AS name FROM pokemon p WHERE p.num = e2.num LIMIT 1)
						  FROM evolutions e2 WHERE e2.num = e.next)) AS next
			FROM evolutions e WHERE prev = $1
			''', num, GLOWING_STAR, STAR))
	if len(chain) == 1:
		return 'This Pokémon does not evolve.'
	start = '\N{BALLOT BOX WITH CHECK}'.join(r['name'] for r in chain[:cur_ind + 1])
	after = chain[cur_ind + 1:]
	chains = []
	if not after:
		chains.append(start)
	else:
		for m in after:
			m = dict(m)
			if not m['next']:
				chains.append(ARROWS[1].join((start, m['name'])))
			else:
				for name in m['next']:
					chains.append(ARROWS[1].join((start, m['name'], name)))
	return '\n'.join(chains)


async def get_player(ctx, uid):
	player_data = await ctx.con.fetchrow("""
								INSERT INTO trainers (user_id) VALUES ($1)
								ON CONFLICT (user_id) DO UPDATE SET user_id=$1
								RETURNING *
								""", uid)
	return player_data


async def get_player_pokemon(ctx, uid):
	player_pokemon = await ctx.con.fetch("""
								   SELECT * FROM found WHERE owner=$1
								   """, uid)
	return player_pokemon


async def get_pokemon(ctx, num):
	mon_info = await ctx.con.fetchrow("""
							 SELECT * FROM pokemon WHERE num=$1
							 """, num)
	return mon_info


async def is_legendary(ctx, num):
	legendary = await ctx.con.fetchval("""
							   SELECT EXISTS(SELECT * FROM pokemon WHERE num=$1 AND legendary AND NOT mythical)
							   """, num)
	return legendary


async def is_mythical(ctx, num):
	mythical = await ctx.con.fetchval("""
							  SELECT EXISTS(SELECT * FROM pokemon WHERE num=$1 and mythical)
							  """, num)
	return mythical


class Pokemon(Menus):
	def __init__(self, bot):
		self.bot = bot
		self.image_path = 'http://pokebot.xyz/botdata/images/pokemon/{}/{}-{}.gif'

###################
#                 #
# INVENTORY       #
#                 #
###################

	@checks.db
	@commands.command(aliases=['inv'])
	@pokechannel()
	async def inventory(self, ctx, *, member: discord.Member = None):
		thumbnail = 'http://pokebot.xyz/botdata/images/misc/backpack.png'
		"""Opens your inventory."""
		member = member or ctx.author
		player_data = await get_player(ctx, member.id)
		inv = player_data['inventory']
		all_items = await ctx.con.fetch('''
			SELECT name FROM items ORDER BY id ASC
			''')
		em = discord.Embed(title=f'{member.name} | {inv["money"]}\ua750')
		items = []
		for item in all_items[1:]:
			if inv.get(item['name']) or item['name'].endswith('ball'):
				key = self.bot.get_emoji_named(item['name']) or item['name']
				items.append(f"{key} | {inv.get(item['name'])}")
		em.set_thumbnail(url=thumbnail)
		em.add_field(name='Inventory', value='\n'.join(items))
		await ctx.send(embed=em, delete_after=60)

###################
#                 #
# REWARD          #
#                 #
###################

	@checks.db
	@commands.command()
	@commands.cooldown(1, 1800, commands.BucketType.user)
	@pokechannel()
	async def reward(self, ctx):
		"""Collect a reward for free every half hour!"""
		user = ctx.author
		player_data = await get_player(ctx, user.id)
		inv = player_data['inventory']
		reward = await ctx.con.fetchrow('''
			SELECT * FROM rewards ORDER BY random() LIMIT 1
			''')
		item, count = reward['name'], reward['num']
		item_name = 'Pokédollar' if item == 'money' else item
		inv[item] = inv.get(item, 0) + count
		await set_inventory(ctx, user.id, inv)
		await ctx.send(f"{user.name} has received {count} **{item_name}{'s' if count != 1 else ''}**!", delete_after=60)

###################
#                 #
# GIVE REWARD     #
#                 #
###################

	@checks.db
	@commands.command(hidden=True)
	@commands.is_owner()
	@pokechannel()
	async def givereward(self, ctx, member: discord.Member = None, item: str = None, count: int = None):
		"""Give a reward for a user!"""
		if item is None:
			await ctx.send('Specify an itme to be awarded',  delete_after=15)
			return
		if count is None:
			count = 1
		user = member or ctx.author
		player_data = await get_player(ctx, user.id)
		inv = player_data['inventory']
		item_name = 'Pokédollar' if item == 'money' else item
		inv[item] = inv.get(item, 0) + count
		await set_inventory(ctx, user.id, inv)
		await ctx.send(f"{user.name} has received {count} **{item_name}{'s' if count != 1 else ''}**!", delete_after=60)
		
		
###################
#                 #
# POKEMON         #
#                 #
###################

	@checks.db
	@commands.group(invoke_without_command=True, aliases=['pokemen', 'pokermon', 'digimon'])
	@commands.cooldown(1, 10, commands.BucketType.user)
	@pokechannel()
	async def pokemon(self, ctx):
		"""Gives you a random Pokemon every 60 seconds!"""
		player_name = ctx.author.name
		player_id = ctx.author.id
		mon = await ctx.con.fetchrow('''
			SELECT num, name, form, form_id, type, legendary, mythical, rand(4294967295) as personality,
			(SELECT form FROM pokemon p2 WHERE p2.num = pokemon.num AND p2.form_id = 0) AS base_form,
			(SELECT ARRAY(SELECT color FROM types WHERE types.name = ANY(type))) AS colors
			FROM pokemon ORDER BY random() LIMIT 1''')
		trainer = await get_player(ctx, player_id)
		inv = trainer['inventory']
		balls = [self.bot.get_emoji_named(ball) for ball in pokeballs if inv.get(ball)]
		star = get_star(mon)
		shiny = is_shiny(trainer, mon['personality'])
		if shiny:
			if mon['base_form']:
				form = mon['base_form'] + ' '
			else:
				form = ''
			form_id = 0
		else:
			if mon['form']:
				form = mon['form'] + ' '
			else:
				form = ''
			form_id = mon['form_id']
		embed = discord.Embed(description=f'A wild **{form}{mon["name"]}**{star}{shiny} appears!' +
							  (f'\nUse a {balls[0]} to catch it!' if balls else ''))
		embed.color = await get_pokemon_color(ctx, mon=mon)
		embed.set_author(icon_url=ctx.author.avatar_url, name=player_name)
		embed.set_image(url=self.image_path.format('normal', mon['num'], 0))
		msg = await ctx.send(embed=embed,  delete_after=60)
		await see(ctx, player_id, mon['num'])
		can_react_with = [*balls, CANCEL]
		for emoji in can_react_with:
			await msg.add_reaction(emoji)
		try:
			def check(reaction, user):
				return (reaction.emoji in can_react_with and
						reaction.message.id == msg.id and
						user == ctx.author)
			reaction, _ = await self.bot.wait_for('reaction_add', check=check, timeout=20)
		except asyncio.TimeoutError:
			embed.description = f'**{form}{mon["name"]}**{star}{shiny} escaped because you took too long! :stopwatch:'
			await msg.edit(embed=embed, delete_after=15)
			await msg.clear_reactions()
			return
		await msg.clear_reactions()
		if reaction.emoji in balls:
			if catch(mon, balls.index(reaction.emoji)):
				embed.description = wrap(f'You caught **{form}{mon["name"]}**{star}{shiny} successfully!',
										 reaction.emoji)
				await msg.edit(embed=embed, delete_after=15)
				level = await ctx.con.fetchval('''
					SELECT level FROM evolutions WHERE next = $1
					''', mon['num']) or 0
				async with ctx.con.transaction():
					await ctx.con.execute('''
						INSERT INTO found (num, form_id, ball, exp, owner, original_owner, personality) VALUES ($1, $2, $3, $4, $5, $6, $7)
						''', mon['num'], form_id, reaction.emoji.name, xp_to_level(level), player_id, player_id, mon['personality'])
			else:
				embed.description = f'**{form}{mon["name"]}**{star}{shiny} has escaped!'
				await msg.edit(embed=embed, delete_after=15)
			inv[reaction.emoji.name] -= 1
			await set_inventory(ctx, player_id, inv)
		else:
			embed.description = wrap(f'You ran away from **{form}{mon["name"]}**{star}{shiny}!', ':chicken:')
			await msg.edit(embed=embed, delete_after=15)

###################
#                 #
# PC              #
#                 #
###################

	@checks.db
	@commands.group(invoke_without_command=True)
	@pokechannel()
	async def pc(self, ctx, *, member: discord.Member = None):
		"""Opens your PC."""
		member = member or ctx.author

		total_pokemon = await ctx.con.fetchval("""
									  SELECT COUNT(DISTINCT num) FROM pokemon
									  """)
		found = await ctx.con.fetch("""
							  WITH p AS (SELECT num, name, form, form_id, legendary, mythical FROM pokemon)
							  SELECT f.num, f.name, original_owner, personality, p.name AS base_name, p.form, legendary, mythical FROM found f
							  JOIN p ON p.num = f.num AND p.form_id = f.form_id
							  WHERE owner = $1 ORDER BY f.num, f.form_id;
							  """, member.id)
		total_found = len(found)
		remaining = total_pokemon - total_found

		legendaries = await ctx.con.fetchval("""
									SELECT COUNT(*) FROM found WHERE owner=$1 AND num=ANY((SELECT num FROM pokemon WHERE legendary=True))
									""", member.id)
		mythics = await ctx.con.fetchval("""
								SELECT COUNT(*) FROM found WHERE owner=$1 AND num=ANY((SELECT num FROM pokemon WHERE mythical=True))
								""", member.id)

		header = f"__**{member.name}'s PC**__"
		if total_found == 0:
			header += " __**is empty.**__"
		if total_found == 0:
			return await ctx.send(header, delete_after=60)
		spacer = SPACER * 21

		key = f'{ARROWS[0]} Click to go back a page.\n{ARROWS[1]} Click to go forward a page.\n{CANCEL}' \
			  f' Click to exit your pc.'

		counts = wrap(f'**{total_found}** collected out of {total_pokemon} total Pokemon. {remaining} left to go!'
					  f'\n**{total_found - mythics - legendaries}** Normal | **{legendaries}** Legendary {STAR}'
					  f' | **{mythics}** Mythical {GLOWING_STAR}', spacer, sep='\n')

		header = '\n'.join([header, 'Use **!pokedex** to see which Pokémon you\'ve encountered!\nUse **!pokedex** ``#`` to take a closer look at a Pokémon!', key, counts])

		trainers = {t['user_id']: t for t in await ctx.con.fetch("""
														   SELECT * FROM trainers WHERE user_id = ANY($1)
														   """, set(m['original_owner'] for m in found))}
		options = []
		done = []
		for mon in found:
			if mon['name'] is None and mon['num'] in done:
				continue
			counter = 0
			if mon['name'] is None:
				shiny = False
				for m in found:
					if m['num'] == mon['num'] and m['name'] is None:
						counter += 1
						if not shiny:
							shiny = is_shiny(trainers[m['original_owner']], m['personality'])
				done.append(mon['num'])
			else:
				shiny = is_shiny(trainers[mon['original_owner']], m['personality'])
			count = f" x{counter}" if counter > 1 else ''
			name = get_name(mon)
			options.append("**{}.** {}{}{}{}".format(mon['num'], name, get_star(mon), shiny, count))
		await self.reaction_menu(options, ctx.author, ctx.channel, 0, per_page=20, code=False, header=header)

###################
#                 #
# POKEDEX         #
#                 #
###################

	async def get_pokedex_embed(self, ctx, mon, shiny=False):
		pokedex = self.bot.get_emoji_named('Pokedex')
		evo = await get_evolution_chain(ctx, mon['num'])
		embed = discord.Embed(description=wrap(f"__{mon['name']}{get_star(mon)}'s Information__", pokedex) +
							  f"\n**ID:** {mon['num']}\n**Type:** {' & '.join(mon['type'])}"
							  f"\n**Evolutions:**\n{evo}")
		embed.color = await get_pokemon_color(ctx, mon=mon)
		return embed

	@checks.db
	@commands.group(invoke_without_command=True)
	@pokechannel()
	async def pokedex(self, ctx, *, member=None):
		"""Shows you your Pokedex through a reaction menu."""
		pokedex = self.bot.get_emoji_named('Pokedex')

		member = await poke_converter(ctx, member) or ctx.author

		total_pokemon = await ctx.con.fetchval("""
									  SELECT COUNT(DISTINCT num) FROM pokemon
									  """)
		if isinstance(member, discord.Member):
			seen = await ctx.con.fetch("""
								 WITH p AS (SELECT num, name, mythical, legendary FROM pokemon WHERE form_id = 0)
								 SELECT s.num, name, mythical, legendary FROM seen s JOIN p ON s.num = p.num
								 WHERE user_id=$1 ORDER BY s.num
								 """, member.id)
			total_found = len(seen)

			legendaries = sum(1 for m in seen if m['legendary'] and not m['mythical'])
			mythicals = sum(1 for m in seen if m['mythical'])

			header = f"__**{member.name}'s Pokedex**__"
			if total_found == 0:
				header += " __**is empty.**__"
			header = wrap(header, pokedex)
			if total_found == 0:
				return await ctx.send(header, delete_after=60)

			spacer = SPACER * 22

			key = f'{ARROWS[0]} Click to go back a page.\n{ARROWS[1]} Click to go forward a page.\n{CANCEL}' \
				  f' Click to exit your pokedex.'

			counts = wrap(f'**{total_found}** encountered out of {total_pokemon} total Pokemon.'
						  f'\n**{total_found - mythicals - legendaries}** Normal | **{legendaries}** Legendary {STAR}'
						  f' | **{mythicals}** Mythical {GLOWING_STAR}', spacer, sep='\n')
			header = '\n'.join([header, 'Use **!pc** to see which Pokémon you own!\nUse **!pokedex** ``#`` to take a closer look at a Pokémon!', key, counts])

			options = []
			for mon in seen:
				options.append("**{}.** {}{}".format(
					mon['num'], mon['name'], get_star(mon)))
			await self.reaction_menu(options, ctx.author, ctx.channel, 0, per_page=20, code=False, header=header)
			return
		elif isinstance(member, int):
			if 0 >= member or member > total_pokemon:
				return await ctx.send(f'Pokemon {member} does not exist.',  delete_after=60)

			image = self.image_path.format('normal', member, 0)
			info = await get_pokemon(ctx, member)
		elif isinstance(member, str):
			pokemon_records = await ctx.con.fetch("""
										  SELECT name FROM pokemon
										  """)
			pokemon_names = [mon['name'] for mon in pokemon_records]
			result = list(process.extractOne(member, pokemon_names))
			if result[1] < 70:
				return await ctx.send(f'Pokemon {member} does not exist.',  delete_after=60)
			pokemon_number = await ctx.con.fetchval("""
										   SELECT num FROM pokemon WHERE name=$1
										   """, result[0])
			info = await get_pokemon(ctx, pokemon_number)
			image = self.image_path.format('normal', info['num'], 0)
		embed = await self.get_pokedex_embed(ctx, info)
		embed.set_image(url=image)
		await ctx.send(embed=embed, delete_after=120)

	@checks.db
	@pokedex.command(name='shiny')
	@pokechannel()
	async def pokedex_shiny(self, ctx, *, pokemon):
		try:
			pokemon = int(pokemon)
		except ValueError:
			pass

		total_pokemon = await ctx.con.fetchval("""
									  SELECT COUNT(DISTINCT num) FROM pokemon
									  """)
		if isinstance(pokemon, int):
			if 0 >= pokemon or pokemon > total_pokemon:
				return await ctx.send(f'Pokemon {pokemon} does not exist.',  delete_after=60)

			image = self.image_path.format('shiny', pokemon, 0)
			info = await get_pokemon(ctx, pokemon)
		elif isinstance(pokemon, str):
			pokemon_records = await ctx.con.fetch("""
										  SELECT name FROM pokemon
										  """)
			pokemon_names = [mon['name'] for mon in pokemon_records]
			result = list(process.extractOne(pokemon, pokemon_names))
			if result[1] < 70:
				return await ctx.send(f'Pokemon {pokemon} does not exist.',  delete_after=60)

			pokemon_number = await ctx.con.fetchval("""
										   SELECT num FROM pokemon WHERE name=$1
										   """, result[0])
			info = await get_pokemon(ctx, pokemon_number)
			image = self.image_path.format('shiny', info['num'], 0)
		embed = await self.get_pokedex_embed(ctx, info, shiny=True)
		embed.set_image(url=image)
		await ctx.send(embed=embed, delete_after=120)

###################
#                 #
# SHOP            #
#                 #
###################

	@checks.db
	@commands.group(invoke_without_command=True, aliases=['store'])
	@pokechannel()
	async def shop(self, ctx, multiple=1):
		"""Allows you to buy more items."""
		if not multiple:
			return
		player_name = ctx.author.name
		player_data = await get_player(ctx, ctx.author.id)
		inventory = player_data['inventory']
		thumbnail = 'http://pokebot.xyz/botdata/images/misc/shop.png'
		title = f'{player_name} | {inventory["money"]}\ua750'
		description = 'Select items to buy{}.'.format(f' in multiples of {multiple}' if multiple > 1 else '')
		balls = await ctx.con.fetch("""
							  SELECT name, price FROM items WHERE price != 0 AND name LIKE '%ball' ORDER BY price
							  """)
		balls = [dict(ball) for ball in balls]
		for ball in balls:
			ball['emoji'] = self.bot.get_emoji_named(ball['name'])
		options = ['{} {}\ua750 **|** Inventory: {}'.format(ball['emoji'], ball['price'],
															inventory.get(ball['name'], 0)) for ball in balls]

		selected = await self.embed_menu(options, 'Shop', ctx.author, ctx.channel, -1,
										 description=description, title=title, thumbnail=thumbnail,
										 return_from=list(range(len(balls))), multi=True,
										 display=[ball['emoji'] for ball in balls])
		if not selected:
			return
		bought = []
		total = 0
		for item in set(selected):
			count = selected.count(item) * multiple
			item_info = balls[item]
			item_price, item_name = item_info['price'], item_info['name']
			price = item_price * count
			after = inventory['money'] - price
			if after < 0:
				continue
			total += price
			bought.extend([item] * count)
			inventory['money'] = after
			inventory[item_name] += count
		if total == 0:
			await ctx.send(f"{player_name} didn't buy anything because they're too poor.", delete_after=60)
		else:
			display = []
			for item in set(bought):
				display.append(str(balls[item]['emoji']))
				count = bought.count(item)
				if count > 1:
					display[-1] += f' x{count}'
			await ctx.send(f'{player_name} bought the following for {total}\ua750:\n' + '\n'.join(display),  delete_after=60)
			await set_inventory(ctx, ctx.author.id, inventory)

###################
#                 #
# SELL            #
#                 #
###################

	@checks.db
	@shop.command()
	@pokechannel()
	async def sell(self, ctx):
		spacer = SPACER * 24
		player_name = ctx.author.name
		user_pokemon = await ctx.con.fetch("""
									 WITH p AS (SELECT num, name, form, form_id, legendary, mythical FROM pokemon)
									 SELECT f.id, f.num, f.name, original_owner, personality,
											p.name AS base_name, p.form, legendary, mythical FROM found f
									 JOIN p ON p.num = f.num AND p.form_id = f.form_id
									 WHERE owner = $1 ORDER BY f.num, f.form_id;
									 """, ctx.author.id)
		user_pokemon = [dict(mon) for mon in user_pokemon]
		player_data = await get_player(ctx, ctx.author.id)
		inventory = player_data['inventory']
		header = f'**{player_name}**,\nSelect Pokemon to sell.\n' + wrap(f'**100**\ua750 Normal | **600**\ua750'
																		 f' Legendary {STAR} | **1000**\ua750'
																		 f' Mythical {GLOWING_STAR}', spacer, sep='\n')
		names = []
		options = []
		trainers = {t['user_id']: t for t in await ctx.con.fetch("""
														   SELECT * FROM trainers WHERE user_id = ANY($1)
														   """, set(m['original_owner'] for m in user_pokemon))}
		for mon in user_pokemon:
			name = get_name(mon)
			mon['shiny'] = is_shiny(trainers[mon['original_owner']], mon['personality'])
			options.append("**{}.** {}{}{}".format(
				mon['num'], name, get_star(mon), mon['shiny']))
			names.append(name)
		if not options:
			await ctx.send("You don't have any pokemon to sell.", delete_after=60)
			return
		selected = await self.reaction_menu(options, ctx.author, ctx.channel, -1, per_page=20, header=header,
											code=False, multi=True, return_from=user_pokemon, display=names)
		if not selected:
			return
		named = []
		sold = []
		sold_ids = []
		total = 0
		selected = unique(selected, key=lambda m: m['id'])
		for mon in sorted(selected, key=lambda m: m['num']):
			if mon['shiny']:
				total += 1000
			if mon['mythical']:
				total += 1000
			elif mon['legendary']:
				total += 600
			else:
				total += 100
			sold_ids.append(mon['id'])
			shiny = False
			if mon['num'] not in named:
				count = 0
				for m in selected:
					if m['num'] == mon['num']:
						count += 1
						shiny = shiny or m['shiny']
				sold.append(f"{mon['base_name']}{shiny}{f' x{count}' if count > 1 else ''}")
				named.append(mon['num'])
		await ctx.con.execute("""
					DELETE FROM found WHERE id = ANY($1)
					""", sold_ids)
		inventory['money'] += total
		await set_inventory(ctx, ctx.author.id, inventory)
		await ctx.send(f'{player_name} sold the following for {total}\ua750:\n' + '\n'.join(sold), delete_after=60)

###################
#                 #
# TRADE           #
#                 #
###################

	@checks.db
	@commands.command()
	@pokechannel()
	async def trade(self, ctx, *, user: discord.Member):
		"""Trade pokemon with another user."""
		author = ctx.author
		if author.id == user.id:
			await ctx.send('You cannot trade with yourself.', delete_after=60)
			return
		channel = ctx.channel
		cancelled = '**{}** cancelled the trade.'
		get_found = await ctx.con.prepare("""
								  WITH p AS (SELECT num, name, form, form_id, legendary, mythical FROM pokemon)
								  SELECT f.id, f.num, f.name, original_owner, personality,
										 p.name AS base_name, p.form, legendary, mythical FROM found f
								  JOIN p ON p.num = f.num AND p.form_id = f.form_id
								  WHERE owner = $1 ORDER BY f.num, f.form_id;
								  """)
		a_found = [dict(m) for m in await get_found.fetch(author.id)]
		b_found = [dict(m) for m in await get_found.fetch(user.id)]
		trainer_ids = set(m['original_owner'] for m in itertools.chain(a_found, b_found))
		trainers = {t['user_id']: t for t in await ctx.con.fetch("""
														   SELECT * FROM trainers WHERE user_id = ANY($1)
														   """, trainer_ids)}

		a_names = []
		a_options = []
		for mon in a_found:
			mon['fname'] = get_name(mon)
			mon['shiny'] = is_shiny(trainers[mon['original_owner']], mon['personality'])
			a_names.append(mon['fname'] + mon['shiny'])
			a_options.append("**{}.** {}{}{}".format(
				mon['num'], mon['fname'], get_star(mon), mon['shiny']))

		b_names = []
		b_options = []
		for mon in b_found:
			mon['fname'] = get_name(mon)
			mon['shiny'] = is_shiny(trainers[mon['original_owner']], mon['personality'])
			b_names.append(mon['fname'] + mon['shiny'])
			b_options.append("**{}.** {}{}{}".format(
				mon['num'], mon['fname'], get_star(mon), mon['shiny']))

		header = '**{.name}**,\nSelect the pokemon you wish to trade with **{.name}**'
		selected = await asyncio.gather(self.reaction_menu(a_options, author, channel, -1, code=False,
														   header=header.format(author, user), return_from=a_found,
														   allow_none=True, multi=True, display=a_names),

										self.reaction_menu(b_options, user, channel, -1, code=False,
														   header=header.format(user, author), return_from=b_found,
														   allow_none=True, multi=True, display=b_names))
		if all(s is None for s in selected):
			await ctx.send('No one responded to the trade.', delete_after=60)
			return
		elif selected[0] is None:
			await ctx.send(cancelled.format(author), delete_after=60)
			return
		elif selected[1] is None:
			await ctx.send(cancelled.format(user), delete_after=60)
			return
		for selections, found, member in zip(selected, (a_found, b_found), (author, user)):
			added_ids = []
			for mon in selections:
				if mon['id'] in added_ids:
					await ctx.send(f'{member.name} selected more {get_name(mon)} than they have.',  delete_after=60)
					return
				added_ids.append(mon['id'])
		accept_msg = await ctx.send("**{}**'s offer: {}\n**{}**'s offer: {}\nDo you accept?".format(
			author.name, '**,** '.join(mon['fname'] for mon in selected[0]) or 'None',
			user.name, '**,** '.join(mon['fname'] for mon in selected[1]) or 'None'))
		await accept_msg.add_reaction(DONE)
		await accept_msg.add_reaction(CANCEL)
		accepted = {author.id: None, user.id: None}
		accept_reaction = None
		reacted = None

		def accept_check(reaction, reaction_user):
			if reaction.message.id != accept_msg.id or reaction.emoji not in (DONE, CANCEL):
				return False
			if reaction.emoji == DONE:
				nonlocal accept_reaction
				accept_reaction = reaction
			if reaction_user.id in accepted:
				accept = reaction.emoji == DONE
				accepted[reaction_user.id] = accept
				if not accept:
					return True
			return all(isinstance(value, bool) for value in accepted.values())

		try:
			with aiohttp.Timeout(60):
				while True:
					await self.bot.wait_for('reaction_add', check=accept_check)
					if accepted[author.id] and accepted[user.id]:
						reacted = await accept_reaction.users().flatten()
						if author in reacted and user in reacted:
							break
					elif any(not value for value in accepted.values()):
						break
		except asyncio.TimeoutError:
			pass

		if all(accepted[u.id] is None for u in (author, user)):
			await ctx.send('No one responded to the trade.', delete_after=60)
			await accept_msg.delete()
			return

		for u in (author, user):
			if reacted and u not in reacted:
				accepted[u.id] = False
			if not accepted[u.id]:
				await ctx.send(f'**{u.name}** declined the trade.', delete_after=60)
				await accept_msg.delete()
				return
		await get_player(ctx, ctx.author.id)
		await get_player(ctx, user.id)
		for selection, old, new in zip(selected, (author, user), (user, author)):
			await see(ctx, new.id, (m['num'] for m in selection))
			await ctx.con.execute("""
						  UPDATE found SET owner=$1 WHERE id=ANY($2) AND owner=$3
						  """, new.id, [mon['id'] for mon in selection], old.id)
		await accept_msg.delete()
		await ctx.send(f'Completed trade between **{author.name}** and **{user.name}**.', delete_after=60)


def setup(bot):
	bot.add_cog(Pokemon(bot))
