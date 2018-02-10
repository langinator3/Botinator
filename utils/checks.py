from discord.ext import commands
import discord.utils
import config

# The permission system of the bot is based on a "just works" basis
# You have permissions and the bot has permissions. If you meet the permissions
# required to execute the command (and the bot does as well) then it goes through
# and you can execute the command.
# Certain permissions signify if the person is a moderator (Manage Server) or an
# admin (Administrator). Having these signify certain bypasses.
# Of course, the owner will always be able to execute commands.

def db(cmd):
	cmd._db = True
	return cmd

def no_delete(cmd):
	cmd._delete_ctx = False
	return cmd

def is_owner_check(ctx):
	try:
		return ctx.message.author.id in config.owner_ids
	except AttributeError:
		return super().is_owner(ctx.message.author)
	
def is_owner():
    return commands.check(is_owner_check)

def check_permissions(ctx, perms):
	msg = ctx.message
	if is_owner():
		return True

	ch = msg.channel
	author = msg.author
	resolved = ch.permissions_for(author)
	return all(getattr(resolved, name, None) == value for name, value in perms.items())

def has_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_permissions(ctx, perms, check=check)
    return commands.check(pred)

async def check_guild_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    if ctx.guild is None:
        return False

    resolved = ctx.author.guild_permissions
    return check(getattr(resolved, name, None) == value for name, value in perms.items())

def has_guild_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_guild_permissions(ctx, perms, check=check)
    return commands.check(pred)

# These do not take channel overrides into account

def role_or_permissions(ctx, check, **perms):
	if check_permissions(ctx, perms):
		return True

	ch = ctx.message.channel
	author = ctx.message.author
	if ch.is_private:
		return False # can't have roles in PMs

	role = discord.utils.find(check, author.roles)
	return role is not None

def mod_or_permissions(**perms):
	def predicate(ctx):
		return role_or_permissions(ctx, lambda r: r.name in ('Bot Mod', 'Bot Admin'), **perms)

	return commands.check(predicate)

def admin_or_permissions(**perms):
	def predicate(ctx):
		return role_or_permissions(ctx, lambda r: r.name == 'Bot Admin', **perms)

	return commands.check(predicate)
	
def serverowner_or_permissions(**perms):
	def predicate(ctx):
		if ctx.message.server is None:
			return False
		server = ctx.message.server
		owner = server.owner

		if ctx.message.author.id == owner.id:
			return True

		return check_permissions(ctx,perms)
	return commands.check(predicate)
	
def serverowner():
	return serverowner_or_permissions()

def admin():
	return admin_or_permissions()

def mod():
	return mod_or_permissions()

