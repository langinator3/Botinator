import asyncio

from discord.ext import commands
import discord

from overwatch_api.core import AsyncOWAPI

ow_cli = AsyncOWAPI(request_timeout=30)
ow_icon = 'https://i.imgur.com/YZ4w2ey.png'

region_convert = {
    'europe': 'eu',
    'korea': 'kr',
    'na': 'us',
    'americas': 'us',
    'america': 'us',
    'china': 'cn',
    'japan': 'jp',
    'global': 'global'
}

platform_convert = {
	'pc': 'pc',
	'xbox': 'xbl',
	'playstation': 'psn'
}

play_convert = {
	'qp': 'quickplay',
	'comp': 'competitive'
}

hero_convert = {
    "ANA": "Ana",
    "BASTION": "Bastion",
    "DIVA": "DVa",
    "GENJI": "Genji",
    "HANZO": "Hanzo",
    "JUNKRAT": "Junkrat",
    "LUCIO": "Lucio",
    "MCCREE": "McCree",
    "MEI": "Mei",
    "MERCY": "Mercy",
    "ORISA": "Orisa",
    "PHARAH": "Pharah",
    "REAPER": "Reaper",
    "REINHARDT": "Reinhardt",
    "ROADHOG": "Roadhog",
    "SOLDIER_76": "Soldier76",
    "SOMBRA": "Sombra",
    "SYMMETRA": "Symmetra",
    "TORBJOERN": "Torbjoern",
    "TRACER": "Tracer",
    "WIDOWMAKER": "Widowmaker",
    "WINSTON": "Winston",
    "ZARYA": "Zarya",
    "ZENYATTA": "Zenyatta"
}

hero_number_convert = {
	'1':'mccree',
	'2':'sombra',
	'3':'genji',
	'4':'pharah',
	'5':'soldier76',
	'6':'tracer',
	'7':'doomfist',
	'8':'widowmaker',
	'9':'hanzo',
	'10':'bastion',
	'11':'mei',
	'12':'junkrat',
	'13':'torbjorn',
	'14':'dva',
	'15':'zarya',
	'16':'winston',
	'17':'orisa',
	'18':'reinhardt',
	'19':'roadhog',
	'20':'lucio',
	'21':'ana',
	'22':'mercy',
	'23':'symmetra',
	'24':'moira'}

def clean_numbers(stats):
	for key in stats:
		try:
			int_value = int(stats[key])
			if int_value != stats[key]:
				int_value = round(stats[key], 2)
			stats.update({key: int_value})
		except ValueError:
			pass
		except TypeError:
			pass
	return stats

def time_convert(time): #32.65
	if time > 24:
		days = int(time/24)
		time = time % 24
	else:
		days = 0
	hours = int(time)
	minutes = int((time*60) % 60)
	seconds = int((time*3600) % 60)
	output = f"{f'{days} day' + {'s' if days >= 2 else ''} + ' ' if days >= 1 else ''}{f'{hours} hr ' if hours >= 1 else ''}{f'{minutes} min ' if minutes >= 1 else ''}{f'{seconds} sec ' if seconds >= 1 else ''}"
	return(output)

class Ow:
	def __init__(self, bot):
		self.bot = bot

###################
#                 #
# OVERWATCH       #
#                 #
###################

	@commands.command(name='overwatch' , aliases=['ow', 'owstats'])
	async def _overwatch(self, message: discord.Message, battletag=None, region=None, platform=None, play=None): #, hero=None
		"""!overwatch [BattleNet ID] [Region] [Platform] [QP/Comp]""" # Maybe add [Hero]
		init_resp = discord.Embed(color=0xff9c00)
		init_resp.set_author(name='Processing information...', icon_url=ow_icon)
		init_resp_msg = await message.channel.send(embed=init_resp)
		if battletag is not None:
			if False:	# hero is not None
				hero = hero.lower()
				if hero in hero_convert:
					hero = hero_convert[hero]
			else:
				hero = None

			hero_list = []
			if True:	# hero in hero_list

				if play is not None:
					play = play.lower()
					if play in play_convert:
						play = play_convert[play]
				else:
					play = 'competitive'

				play_list = ['competitive', 'quickplay']
				if play in play_list:

					if platform is not None:
						platform = platform.lower()
						if platform in platform_convert:
							platform = platform_convert[platform]
						if platform is not 'pc':
							region = 'global'
					else:
						platform = 'pc'
					
					platform_list = ['pc', 'xbl', 'psn']
					if platform in platform_list:

						if region is not None:
							region = region.lower()
							if region in region_convert:
								region = region_convert[region]
						else:
							region = 'us'

						region_list = ['eu', 'kr', 'us', 'cn', 'jp', 'global']
						if region in region_list:
							# noinspection PyBroadException
							try:
								profile = await ow_cli.get_profile(battletag, regions=region, platform=platform)	# Gets profile from Blizzard
								timeout = False
								failed = False
							except asyncio.TimeoutError:
								profile = None
								timeout = True
								failed = False
							except Exception:
								profile = None
								timeout = False
								failed = True
							if not failed:
								if not timeout:
									if profile:
										profile = profile[region]
										if play is 'competitive':
											stats = profile['stats'][play]
										#	heroes = profile['heroes']['playtime'][play]
											gen = stats['overall_stats']
											gms = stats['game_stats']
										elif play is not 'competitive' or gms.get("games_played") >= 10:
											play = 'quickplay'
											stats = profile['stats'][play]
										#	heroes = profile['heroes']['playtime'][play]
											gen = stats['overall_stats']
											gms = stats['game_stats']

										if gen['prestige']:
											level = f'{(gen["prestige"] * 100) + gen["level"]}'
										else:
											level = f'{gen.get("level")}'

										#generate profile links and compose them into a string for output
										moLink = "https://masteroverwatch.com/profile/pc/global/" + ow_cli.sanitize_battletag(battletag)
										obLink = "https://www.overbuff.com/players/pc/" + ow_cli.sanitize_battletag(battletag)
										owLink = "https://playoverwatch.com/en-us/career/pc/" + ow_cli.sanitize_battletag(battletag)
										profLinks = "[Profile](" + owLink + ") | [Overbuff](" + obLink + ") | [Master Overwatch](" + moLink + ")"

										if play is 'competitive':
											# Competitive Stats
											response=discord.Embed(title="", description=f'{profLinks}\nRegion: {region.upper()} | Platform: {platform.upper()}\n{gms.get("games_played")} {play} games played ({str(round((int(gms.get("games_won")) / int((gms.get("games_played")) - int(gms.get("games_tied")))) * 100, 0))}% won) over {gms.get("time_played")} hours', color=0xff9c00)
											
											# List who the stats are for
											response.set_author(name=battletag, icon_url=gen.get("tier_image"), url=owLink)
											# Response.set_thumbnail(url=gen.get("avatar"))	# Removed as 3 inlines are needed and cannot have that and thumbnail

											response.add_field(name='Level', value=level, inline=True)
											response.add_field(name='Skill Rating', value=gen.get("comprank"), inline=True)
											response.add_field(name='Most Played Hero', value='TBD', inline=True)

											response.add_field(name='**Eliminations**', value=f'**Average:** {str("{:,.2f}".format((int(gms.get("eliminations")) / int(gms.get("games_played")))))}\n**Most:** {"{:,.0f}".format(gms.get("eliminations_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("eliminations"))}', inline=True)
											response.add_field(name='**Damage**', value=f'**Average:** {str("{:,.0f}".format((int(gms.get("hero_damage_done")) / int(gms.get("games_played")))))}\n**Most:** {"{:,.0f}".format(gms.get("hero_damage_done_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("hero_damage_done"))}', inline=True)
											response.add_field(name='**Healing**', value=f'**Average:** {str("{:,.0f}".format((int(gms.get("healing_done")) / int(gms.get("games_played")))))}\n**Most:** {"{:,.0f}".format(gms.get("healing_done_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("healing_done_most_in_game"))}', inline=True)
											
											response.add_field(name='Solo Kills', value=f'**Average:** {str("{:,.2f}".format((int(gms.get("solo_kills")) / int(gms.get("games_played")))))}\n**Most:** {"{:,.0f}".format(gms.get("solo_kills_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("solo_kills"))}', inline=True)
											response.add_field(name='Objective Kills', value=f'**Average:** {str("{:,.2f}".format((int(gms.get("objective_kills")) / int(gms.get("games_played")))))}\n**Most:** {"{:,.0f}".format(gms.get("objective_kills_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("objective_kills"))}', inline=True)
											response.add_field(name='Final Blows', value=f'**Average:** {str("{:,.2f}".format((int(gms.get("final_blows")) / int(gms.get("games_played")))))}\n**Most:** {"{:,.0f}".format(gms.get("final_blows_most_in_game"))}\n**Total Melee:** {"{:,.0f}".format(gms.get("melee_final_blows"))}\n**Total:** {"{:,.0f}".format(gms.get("final_blows"))}', inline=True)
											
											response.add_field(name='Environmental', value=f'**Kills:** {gms.get("environmental_kills")}\n\n**Total Deaths:** {gms.get("deaths")}', inline=True)
											response.add_field(name='Offensive Assists', value=f'**Average:** {str("{:,.0f}".format((int(gms.get("offensive_assists")) / int(gms.get("games_played")))))}\n**Most:** {"{:,.0f}".format(gms.get("offensive_assists_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("offensive_assists"))}', inline=True)
											response.add_field(name='Defensive Assists', value=f'**Average:** {str("{:,.0f}".format((int(gms.get("defensive_assists")) / int(gms.get("games_played")))))}\n**Most:** {"{:,.0f}".format(gms.get("defensive_assists_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("defensive_assists"))}', inline=True)
											
											response.add_field(name='Objective Time', value=f'**Average:** {time_convert(int(gms.get("objective_time")) / int(gms.get("games_played")))}\n**Most:** {time_convert(gms.get("objective_time_most_in_game"))}\n**Total:** {time_convert(gms.get("objective_time"))}', inline=True)
											response.add_field(name='Time On Fire', value=f'**Average:** {time_convert(int(gms.get("time_spent_on_fire")) / int(gms.get("games_played")))}\n**Most:** {time_convert(gms.get("time_spent_on_fire_most_in_game"))}\n**Total:** {time_convert(gms.get("time_spent_on_fire"))}', inline=True)
										else:
											# Quickplay Stats
											response=discord.Embed(title="", description=f'{profLinks}\nRegion: {region.upper()} | Platform: {platform.upper()}\n{gms.get("time_played")} hours of {play} games played!', color=0xff9c00)
											
											# List who the stats are for
											response.set_author(name=battletag, icon_url=gen.get("tier_image"), url=owLink)
											# Response.set_thumbnail(url=gen.get("avatar"))	# Removed as 3 inlines are needed and cannot have that and thumbnail

											response.add_field(name='Level', value=level, inline=True)
											response.add_field(name='Skill Rating', value=gen.get("comprank"), inline=True)
											response.add_field(name='Most Played Hero', value='TBD', inline=True)

											response.add_field(name='**Eliminations**', value=f'**Most:** {"{:,.0f}".format(gms.get("eliminations_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("eliminations"))}', inline=True)
											response.add_field(name='**Damage**', value=f'**Most:** {"{:,.0f}".format(gms.get("hero_damage_done_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("hero_damage_done"))}', inline=True)
											response.add_field(name='**Healing**', value=f'**Most:** {"{:,.0f}".format(gms.get("healing_done_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("healing_done_most_in_game"))}', inline=True)
											
											response.add_field(name='Solo Kills', value=f'**Most:** {"{:,.0f}".format(gms.get("solo_kills_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("solo_kills"))}', inline=True)
											response.add_field(name='Objective Kills', value=f'**Most:** {"{:,.0f}".format(gms.get("objective_kills_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("objective_kills"))}', inline=True)
											response.add_field(name='Final Blows', value=f'**Most:** {"{:,.0f}".format(gms.get("final_blows_most_in_game"))}\n**Total Melee:** {"{:,.0f}".format(gms.get("melee_final_blows"))}\n**Total:** {"{:,.0f}".format(gms.get("final_blows"))}', inline=True)
											
											response.add_field(name='Environmental', value=f'**Kills:** {gms.get("environmental_kills")}\n\n**Total Deaths:** {gms.get("deaths")}', inline=True)
											response.add_field(name='Offensive Assists', value=f'**Most:** {"{:,.0f}".format(gms.get("offensive_assists_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("offensive_assists"))}', inline=True)
											response.add_field(name='Defensive Assists', value=f'**Most:** {"{:,.0f}".format(gms.get("defensive_assists_most_in_game"))}\n**Total:** {"{:,.0f}".format(gms.get("defensive_assists"))}', inline=True)
											
											response.add_field(name='Objective Time', value=f'**Most:** {time_convert(gms.get("objective_time_most_in_game"))}\n**Total:** {time_convert(gms.get("objective_time"))}', inline=True)
											response.add_field(name='Time On Fire', value=f'**Most:** {time_convert(gms.get("time_spent_on_fire_most_in_game"))}\n**Total:** {time_convert(gms.get("time_spent_on_fire"))}', inline=True)

									#	await message.channel.send(heroes)	# Hero Time checking

										footer_text = 'Click the battletag at the top to see the user\'s profile.'
										response.set_footer(text=footer_text, icon_url=ow_icon)
									else:
										response = discord.Embed(color=0x696969, title='🔍 That Battletag exists but I could not find stats for the specified region.')
								else:
									response = discord.Embed(color=0xBE1931, title='❗ Sorry, my request timed out.')
							else:
								response = discord.Embed(color=0xBE1931, title='❗ Sorry, I failed to retrieve any data.')
						else:
							region_error_text = f'Supported: {", ".join(region_list)}.\nOr: {", ".join(list(region_convert))}.'
							response = discord.Embed(color=0xBE1931)
							response.add_field(name='❗ Invalid region.', value=region_error_text)
					else:
						platform_error_text = f'Supported: {", ".join(platform_list)}.\nOr: {", ".join(list(platform_convert))}.'
						response = discord.Embed(color=0xBE1931)
						response.add_field(name='❗ Invalid platform.', value=platform_error_text)
				else:
					play_error_text = f'Supported: {", ".join(play_list)}.\nOr: {", ".join(list(play_convert))}.'
					response = discord.Embed(color=0xBE1931)
					response.add_field(name='❗ Invalid play.', value=play_error_text)
			else:
				hero_error_text = f'Supported: {", ".join(hero_list)}.\nOr: {", ".join(list(hero_convert))}.'
				response = discord.Embed(color=0xBE1931)
				response.add_field(name='❗ Invalid hero.', value=hero_error_text)
		else:
			response = discord.Embed(color=0xBE1931, title='❗ Battletag needed.')
		await init_resp_msg.edit(embed=response, delete_after=30)

def setup(bot):
	bot.add_cog(Ow(bot))