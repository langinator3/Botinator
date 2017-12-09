from discord.ext import commands
import discord.utils
import config

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

