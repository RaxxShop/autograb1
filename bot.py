import discord
from discord.ext import commands
import json
import os
import asyncio

# ══════════════════════════════════════════
#           CONFIGURATION DU BOT
# ══════════════════════════════════════════

TOKEN = "TON_TOKEN_ICI"          # Remplace par ton token Discord
PREFIX = "!"
STAFF_ROLE_NAME = "Staff"        # Nom du rôle staff à donner
OWNER_IDS = [123456789]          # Ton ID Discord ici (pour les commandes admin)

# Fichier pour stocker les commandes custom
CUSTOM_COMMANDS_FILE = "custom_commands.json"

# ══════════════════════════════════════════
#           SETUP DU BOT
# ══════════════════════════════════════════

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

def load_custom_commands():
    if os.path.exists(CUSTOM_COMMANDS_FILE):
        with open(CUSTOM_COMMANDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_custom_commands(data):
    with open(CUSTOM_COMMANDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

custom_commands = load_custom_commands()

# ══════════════════════════════════════════
#           EVENTS
# ══════════════════════════════════════════

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")
    print(f"📋 Préfixe : {PREFIX}")
    print(f"🖥️  Serveurs : {len(bot.guilds)}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"{PREFIX}help")
    )

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Vérifier les commandes custom
    content = message.content.lower()
    guild_id = str(message.guild.id) if message.guild else None

    if guild_id and content.startswith(PREFIX):
        cmd_name = content[len(PREFIX):].split()[0]
        guild_cmds = custom_commands.get(guild_id, {})
        if cmd_name in guild_cmds:
            embed = discord.Embed(
                description=guild_cmds[cmd_name],
                color=0x5865F2
            )
            embed.set_footer(text=f"Commande custom : {PREFIX}{cmd_name}")
            await message.channel.send(embed=embed)
            return

    await bot.process_commands(message)

# ══════════════════════════════════════════
#           VÉRIFICATIONS
# ══════════════════════════════════════════

def is_owner():
    async def predicate(ctx):
        return ctx.author.id in OWNER_IDS
    return commands.check(predicate)

def is_staff():
    async def predicate(ctx):
        staff_role = discord.utils.get(ctx.guild.roles, name=STAFF_ROLE_NAME)
        return staff_role in ctx.author.roles or ctx.author.id in OWNER_IDS
    return commands.check(predicate)

# ══════════════════════════════════════════
#      📨 DM ALL — ENVOYER À TOUT LE SERV
# ══════════════════════════════════════════

@bot.command(name="dmall")
@is_owner()
async def dm_all(ctx, *, message: str):
    """
    !dmall <message>
    Envoie un DM à tous les membres du serveur.
    """
    guild = ctx.guild
    success = 0
    failed = 0

    embed_dm = discord.Embed(
        title=f"📨 Message de {guild.name}",
        description=message,
        color=0x5865F2
    )
    embed_dm.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed_dm.set_footer(text=f"Envoyé par {ctx.author}", icon_url=ctx.author.display_avatar.url)

    status_embed = discord.Embed(
        title="⏳ Envoi en cours...",
        description=f"Envoi à **{len([m for m in guild.members if not m.bot])}** membres...",
        color=0xFFA500
    )
    status_msg = await ctx.send(embed=status_embed)

    for member in guild.members:
        if member.bot:
            continue
        try:
            await member.send(embed=embed_dm)
            success += 1
        except discord.Forbidden:
            failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.5)  # Anti-ratelimit

    result_embed = discord.Embed(
        title="✅ DM All terminé !",
        color=0x57F287
    )
    result_embed.add_field(name="✅ Envoyés", value=str(success), inline=True)
    result_embed.add_field(name="❌ Échoués", value=str(failed), inline=True)
    result_embed.add_field(name="📝 Message", value=message[:200], inline=False)
    await status_msg.edit(embed=result_embed)

# ══════════════════════════════════════════
#      🎭 COMMANDE STAFF — DONNE LE RÔLE
# ══════════════════════════════════════════

@bot.command(name="staff")
async def get_staff(ctx):
    """
    !staff
    Donne le rôle Staff à celui qui utilise la commande.
    """
    staff_role = discord.utils.get(ctx.guild.roles, name=STAFF_ROLE_NAME)

    if not staff_role:
        # Créer le rôle s'il n'existe pas
        try:
            staff_role = await ctx.guild.create_role(
                name=STAFF_ROLE_NAME,
                color=discord.Color.gold(),
                hoist=True,
                mentionable=True,
                reason="Rôle Staff créé automatiquement par le bot"
            )
        except discord.Forbidden:
            return await ctx.send("❌ Je n'ai pas la permission de créer des rôles !")

    if staff_role in ctx.author.roles:
        embed = discord.Embed(
            description=f"⚠️ Tu as déjà le rôle **{STAFF_ROLE_NAME}** !",
            color=0xFEE75C
        )
        return await ctx.send(embed=embed)

    try:
        await ctx.author.add_roles(staff_role, reason=f"A utilisé {PREFIX}staff")
        embed = discord.Embed(
            title="🎉 Rôle obtenu !",
            description=f"{ctx.author.mention} vient d'obtenir le rôle **{STAFF_ROLE_NAME}** !",
            color=0xFFD700
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ Je n'ai pas la permission de gérer les rôles !")

# ══════════════════════════════════════════
#      🔧 COMMANDES CUSTOM — CRÉER/GÉRER
# ══════════════════════════════════════════

@bot.command(name="addcmd")
@is_owner()
async def add_command(ctx, name: str, *, response: str):
    """
    !addcmd <nom> <réponse>
    Crée une commande custom.
    """
    guild_id = str(ctx.guild.id)
    if guild_id not in custom_commands:
        custom_commands[guild_id] = {}

    custom_commands[guild_id][name.lower()] = response
    save_custom_commands(custom_commands)

    embed = discord.Embed(
        title="✅ Commande créée !",
        color=0x57F287
    )
    embed.add_field(name="Commande", value=f"`{PREFIX}{name}`", inline=True)
    embed.add_field(name="Réponse", value=response[:200], inline=True)
    await ctx.send(embed=embed)

@bot.command(name="delcmd")
@is_owner()
async def del_command(ctx, name: str):
    """
    !delcmd <nom>
    Supprime une commande custom.
    """
    guild_id = str(ctx.guild.id)
    if guild_id in custom_commands and name.lower() in custom_commands[guild_id]:
        del custom_commands[guild_id][name.lower()]
        save_custom_commands(custom_commands)
        embed = discord.Embed(
            description=f"✅ Commande `{PREFIX}{name}` supprimée.",
            color=0x57F287
        )
    else:
        embed = discord.Embed(
            description=f"❌ Commande `{PREFIX}{name}` introuvable.",
            color=0xED4245
        )
    await ctx.send(embed=embed)

@bot.command(name="listcmd")
async def list_commands(ctx):
    """
    !listcmd
    Liste toutes les commandes custom du serveur.
    """
    guild_id = str(ctx.guild.id)
    guild_cmds = custom_commands.get(guild_id, {})

    embed = discord.Embed(title="📋 Commandes custom", color=0x5865F2)

    if not guild_cmds:
        embed.description = "Aucune commande custom créée.\nUtilise `!addcmd <nom> <réponse>` pour en créer une !"
    else:
        cmds_list = "\n".join([f"`{PREFIX}{k}` → {v[:50]}{'...' if len(v) > 50 else ''}" for k, v in guild_cmds.items()])
        embed.description = cmds_list

    await ctx.send(embed=embed)

# ══════════════════════════════════════════
#      🚀 MOVE — DÉPLACER DES MEMBRES
# ══════════════════════════════════════════

@bot.command(name="move")
@is_staff()
async def move_member(ctx, member: discord.Member, *, channel_name: str):
    """
    !move @membre <nom du salon vocal>
    Déplace un membre vers un autre salon vocal.
    """
    # Trouver le salon vocal par nom
    target_channel = discord.utils.find(
        lambda c: c.name.lower() == channel_name.lower() and isinstance(c, discord.VoiceChannel),
        ctx.guild.channels
    )

    if not target_channel:
        # Cherche partiellement
        target_channel = discord.utils.find(
            lambda c: channel_name.lower() in c.name.lower() and isinstance(c, discord.VoiceChannel),
            ctx.guild.channels
        )

    if not target_channel:
        embed = discord.Embed(
            description=f"❌ Salon vocal `{channel_name}` introuvable.",
            color=0xED4245
        )
        return await ctx.send(embed=embed)

    if not member.voice:
        embed = discord.Embed(
            description=f"❌ {member.mention} n'est pas dans un salon vocal.",
            color=0xED4245
        )
        return await ctx.send(embed=embed)

    try:
        await member.move_to(target_channel, reason=f"Déplacé par {ctx.author}")
        embed = discord.Embed(
            title="🚀 Membre déplacé !",
            description=f"{member.mention} a été déplacé vers **{target_channel.name}**",
            color=0x57F287
        )
        embed.set_footer(text=f"Par {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ Je n'ai pas la permission de déplacer ce membre !")

@bot.command(name="moveall")
@is_staff()
async def move_all(ctx, from_channel: str, *, to_channel: str):
    """
    !moveall <salon source> <salon destination>
    Déplace tous les membres d'un salon vers un autre.
    """
    source = discord.utils.find(
        lambda c: from_channel.lower() in c.name.lower() and isinstance(c, discord.VoiceChannel),
        ctx.guild.channels
    )
    target = discord.utils.find(
        lambda c: to_channel.lower() in c.name.lower() and isinstance(c, discord.VoiceChannel),
        ctx.guild.channels
    )

    if not source or not target:
        return await ctx.send("❌ Un des salons vocaux est introuvable.")

    members = source.members
    if not members:
        return await ctx.send(f"❌ Aucun membre dans **{source.name}**.")

    moved = 0
    for member in members:
        try:
            await member.move_to(target)
            moved += 1
        except:
            pass

    embed = discord.Embed(
        title="🚀 Move All terminé !",
        description=f"**{moved}** membre(s) déplacé(s) de **{source.name}** vers **{target.name}**",
        color=0x57F287
    )
    await ctx.send(embed=embed)

# ══════════════════════════════════════════
#      📢 ANNOUNCE — EMBED DANS UN SALON
# ══════════════════════════════════════════

@bot.command(name="announce")
@is_staff()
async def announce(ctx, channel: discord.TextChannel, *, message: str):
    """
    !announce #salon <message>
    Envoie une annonce dans un salon.
    """
    embed = discord.Embed(
        description=message,
        color=0x5865F2
    )
    embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    embed.set_footer(text=f"Annonce par {ctx.author}", icon_url=ctx.author.display_avatar.url)

    await channel.send(embed=embed)
    await ctx.message.add_reaction("✅")

# ══════════════════════════════════════════
#      📊 HELP — LISTE DES COMMANDES
# ══════════════════════════════════════════

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(
        title="📋 Liste des commandes",
        description=f"Préfixe : `{PREFIX}`",
        color=0x5865F2
    )

    embed.add_field(
        name="👑 Owner uniquement",
        value=(
            f"`{PREFIX}dmall <message>` — DM tout le serveur\n"
            f"`{PREFIX}addcmd <nom> <réponse>` — Créer une commande custom\n"
            f"`{PREFIX}delcmd <nom>` — Supprimer une commande custom"
        ),
        inline=False
    )
    embed.add_field(
        name="🛡️ Staff & Owner",
        value=(
            f"`{PREFIX}move @membre <salon>` — Déplacer un membre\n"
            f"`{PREFIX}moveall <source> <destination>` — Déplacer tout un salon\n"
            f"`{PREFIX}announce #salon <message>` — Envoyer une annonce"
        ),
        inline=False
    )
    embed.add_field(
        name="🌍 Tout le monde",
        value=(
            f"`{PREFIX}staff` — Obtenir le rôle Staff\n"
            f"`{PREFIX}listcmd` — Voir les commandes custom"
        ),
        inline=False
    )
    embed.set_footer(text=f"Bot by {bot.user}", icon_url=bot.user.display_avatar.url if bot.user else None)
    await ctx.send(embed=embed)

# ══════════════════════════════════════════
#           GESTION DES ERREURS
# ══════════════════════════════════════════

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        embed = discord.Embed(
            description="❌ Tu n'as pas la permission d'utiliser cette commande.",
            color=0xED4245
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            description=f"❌ Argument manquant : `{error.param.name}`\nUtilise `{PREFIX}help` pour voir l'usage.",
            color=0xED4245
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MemberNotFound):
        embed = discord.Embed(
            description="❌ Membre introuvable.",
            color=0xED4245
        )
        await ctx.send(embed=embed)
    else:
        print(f"Erreur : {error}")

# ══════════════════════════════════════════
#           LANCEMENT DU BOT
# ══════════════════════════════════════════

bot.run(TOKEN)
