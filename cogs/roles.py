import discord
import asyncio

from discord.ext import commands

from cogs.menus import Menus, ARROWS, CANCEL
from utils.utils import wrap
from utils import errors


def rolechannel():
	def check(ctx):
		if ctx.channel.name in ['role-assigning']:
			return True
		raise errors.WrongChannel(discord.utils.get(ctx.guild.channels, name='role-assigning'))
	return commands.check(check)


class ROLES(Menus):
	def __init__(self, bot):
		self.bot = bot
		self.game_aliases = {
			'Cards Against Humanity': ("CARDSAGAINSTHUMANITY", "CAH", "CARDS", "CARD"),
			'Destiny 2': ("DESTINY2", "DESTINY"),
			'Dota 2': ("DOTA", "DOTATWO", "DOTA2"),
			'Fortnite': ("FORTNITE", "BATTLEROYAL", "POORMANSPUBG"),
			'Heroes of The Storm': ("HOTS", "HEROESOFTHESTORM"),
			'League of Legends': ("LEAGUEOFLEGENDS", "LOL", "LEAGUE", "IMFUCKINGTILTED", "TILTED"),
			'Minecraft': ("MINECRAFT", "MC", "NERD"),
			'Overwatch': ("OVERWATCH", "OW"),
			'Paladins': ("PALADINS"),
			'PUBG': ("PUBG", "PLAYERUNKNOWNBATTLEGROUND", "PLAYERUNKNOWNBATTLEGROUNDS", "PLAYERUNKNOWN", "BATTLEGROUND"),
			'Pickup Game': ("PUG", "PICKUP", "PICKUPGAME", "PICKUPGAMES"),
			
			'Asia': ("ASIA"),
			'Europe': ("EUROPE", "EU"),
			'Australia': ("AUSTRALIA"),
			'Pacific Standard Time': ("PACIFIC", "PACIFICSTANDARDTIME"),
			'Mountain Standard Time': ("MOUNTAIN", "MOUNTAINSTANDARDTIME"),
			'Central Standard Time': ("CENTRAL", "CENTRALSTANDARDTIME"),
			'Eastern Standard Time': ("EASTERN", "EASTERNSTANDARDTIME"),
			'Oceanic': ("OCEANIC")
		}

###################
#                 #
# ROLES           #
#                 #
###################

	async def game_role_helper(self, ctx, member, game_name, toggle):
		if toggle:
			say_temps = (':x: You\'re already assigned to the **{role}** role.',
						 ':white_check_mark: Assigned **{role}** role.',
						 ':x: **Invalid Game**.\nWant a game added? Ask *__Langinator3__* to add it.',
						 ':x: You\'re already assigned to a time zone.',
						 ':x: **Invalid Time Zone**.\nWant a time zone added? Ask *__Langinator3__* to add it.',)
		else:
			say_temps = (':x: You\'re not assigned to the **{role}** role.',
						 ':white_check_mark: Removed **{role}** role.',
						 ':x: **Invalid Game**.\nWant a game added? Ask *__Langinator3__* to add it.',
						 ':white_check_mark: Removed **{role}** time zone.',
						 ':x: **Invalid Time Zone**.\nWant a time zone added? Ask *__Langinator3__* to add it.',)
		
		changed = False
		role_name = None
		for game, aliases in self.game_aliases.items():
			if game_name.upper().replace(' ', '') in aliases:
				role = discord.utils.get(ctx.guild.roles, name=game)
				role_name = game
				if toggle:
					if role not in member.roles:
						await member.add_roles(role)
						changed = True
				else:
					if role in member.roles:
						await member.remove_roles(role)
						changed = True
				break
		else:
			changed = 2
		await ctx.send(say_temps[int(changed)].format(role=role_name), delete_after=20)

	@rolechannel()
	@commands.group(aliases=['role'])
	async def roles(self, ctx):
		"""Shows role module settings."""
		if ctx.invoked_subcommand is None:
			await self.bot.send_help(ctx)
		
	@rolechannel()
	@roles.command(name='add', aliases=['give'])
	async def assign(self, ctx, *, game_name: str):
		"""Adds you to a specified game role."""
		await self.game_role_helper(ctx, ctx.author, game_name, True)

###################
#                 #
# STOP            #
#                 #
###################

	async def stop_all_helper(self, ctx, member):
		temp = ':clock{}: Removing roles.. *please wait*...'
		emsg = await ctx.send(temp.format(1))
		for i, game in enumerate(self.game_aliases.keys()):  # Fix logic to only remove roles the member has
			await asyncio.sleep(1)
			try:
				role = discord.utils.get(ctx.guild.roles, name=game)
				await member.remove_roles(role)
			except discord.Forbidden:
				pass
			await emsg.edit(content=temp.format(((i * 2) % 12) + 1))
		await emsg.edit(content=':white_check_mark: Removed **all** game roles.', delete_after=15)

	@rolechannel()
	@roles.command(name='stop', aliases=['remove'])
	async def unnasign(self, ctx, *, game_name: str):
		"""Removes you from a specified game role."""
		await self.game_role_helper(ctx, ctx.author, game_name, False)

	@rolechannel()
	@roles.command(name='stopall', aliases=['removeall'])
	async def unassignall(self, ctx):
		"""Remove all your game roles."""
		await self.stop_all_helper(ctx, ctx.author)

###################
#                 #
# LIST            #
#                 #
###################

	@rolechannel()
	@roles.command(name='list')
	async def list_roles(self, ctx):
		"""Lists all of the game roles."""
		roles = sorted(self.game_aliases.keys())
		header = "**Game List**"
		spacer = '-=-=-=--=-=-=--=-=-=--=-=-=-=-=-=-=-=-=-=-=-=-=-=-'
		key = f'{ARROWS[0]} Click to go back a page.\n{ARROWS[1]} Click to go forward a page.\n{CANCEL} Click to exit the list.'
		info = wrap('To assign yourself one of these roles just use **!roles add ``Game``**.', spacer, sep='\n')
		header = '\n'.join([header, key, info])
		await self.reaction_menu(roles, ctx.author, ctx.channel, 0, per_page=20, timeout=120, code=False, header=header, return_from=roles)


def setup(bot):
	bot.add_cog(ROLES(bot))
