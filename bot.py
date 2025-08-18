import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
from datetime import datetime

# --- CONFIG ---
DISCORD_TOKEN = "your_discord_bot_token"
HYPIXEL_API_KEY = "your_hypixel_api_key"
STAFF_ROLE_ID =   # staff role as integer
GUILD_NAME = "your_guild_name"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
HYPIXEL_BASE = "https://api.hypixel.net"

# --- Helpers ---

async def fetch_json(session, url, params=None):
    async with session.get(url, params=params) as resp:
        return await resp.json()

def circle(color: str) -> str:
    return {
        "green": ":green_circle:",
        "yellow": ":yellow_circle:",
        "red": ":red_circle:"
    }.get(color, ":white_circle:")

def get_bedwars_rating(wins, stars):
    return wins >= 2500 and stars >= 300

def get_duels_rating(wins, wlr):
    return wins >= 7500 and wlr >= 2.5

def get_skywars_rating(stars):
    return stars >= 10

def get_skyblock_rating(level):
    return level >= 140

def get_guild_circle(gexp):
    if gexp >= 100000:
        return "green"
    else:
        return "red"

async def get_uuid(session, username):
    url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
    data = await fetch_json(session, url)
    return data.get("id")

async def get_player_data(session, uuid):
    url = f"{HYPIXEL_BASE}/player"
    data = await fetch_json(session, url, {"key": HYPIXEL_API_KEY, "uuid": uuid})
    return data.get("player")

async def get_guild_by_player(session, uuid):
    url = f"{HYPIXEL_BASE}/guild"
    data = await fetch_json(session, url, {"key": HYPIXEL_API_KEY, "player": uuid})
    return data.get("guild")

async def get_guild_by_name(session):
    url = f"{HYPIXEL_BASE}/guild"
    data = await fetch_json(session, url, {"key": HYPIXEL_API_KEY, "name": GUILD_NAME})
    return data.get("guild")

def get_weekly_gexp(exp_history):
    return sum(exp_history.values())

# --- Staff Check ---

def is_staff():
    async def predicate(interaction: discord.Interaction):
        role = discord.utils.get(interaction.user.roles, id=STAFF_ROLE_ID)
        if role:
            return True
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- Events ---

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# --- /reqcheck Command ---

@bot.tree.command(name="reqcheck", description="Check a player's stats against guild requirements")
@app_commands.describe(username="Minecraft username")
@is_staff()
async def reqcheck(interaction: discord.Interaction, username: str):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        uuid = await get_uuid(session, username)
        if not uuid:
            return await interaction.followup.send("❌ Could not find that player.")

        player = await get_player_data(session, uuid)
        if not player:
            return await interaction.followup.send("❌ Failed to fetch player data.")

        name = player.get("displayname", "Unknown")
        stats = player.get("stats", {})
        achievements = player.get("achievements", {})

        guild = await get_guild_by_player(session, uuid)
        gexp = 0
        guild_name = "None"
        if guild:
            guild_name = guild.get("name", "Unknown")
            member = next((m for m in guild["members"] if m["uuid"] == uuid), None)
            if member:
                gexp = get_weekly_gexp(member.get("expHistory", {}))

        # Bedwars
        bedwars_wins = stats.get("Bedwars", {}).get("wins_bedwars", 0)
        bedwars_stars = achievements.get("bedwars_level", 0)
        fk = stats.get("Bedwars", {}).get("final_kills_bedwars", 0)
        fd = stats.get("Bedwars", {}).get("final_deaths_bedwars", 1)
        fkdr = round(fk / max(1, fd), 2)
        bedwars_ok = get_bedwars_rating(bedwars_wins, bedwars_stars)

        # Duels
        duels_wins = stats.get("Duels", {}).get("wins", 0)
        duels_losses = stats.get("Duels", {}).get("losses", 1)
        duels_kills = stats.get("Duels", {}).get("kills", 0)
        duels_wlr = round(duels_wins / max(1, duels_losses), 2)
        duels_ok = get_duels_rating(duels_wins, duels_wlr)

        # Skywars
        skywars_stars = achievements.get("skywars_you_re_a_star", 0)
        skywars_wins = stats.get("SkyWars", {}).get("wins", 0)
        skywars_losses = stats.get("SkyWars", {}).get("losses", 1)
        skywars_wlr = round(skywars_wins / max(1, skywars_losses), 2)
        skywars_ok = get_skywars_rating(skywars_stars)

        # Skyblock
        skyblock_level = achievements.get("skyblock_leveling", 0)
        skyblock_ok = get_skyblock_rating(skyblock_level)

        # Embed
        embed = discord.Embed(
            description=f"Below is the requirement check for **{name}**!",
            color=discord.Color.dark_purple()
        )
        embed.set_author(name=f"{name} | {guild_name}", icon_url=f"https://minotar.net/helm/{name}/150.png")
        embed.set_image(url="https://cdn.discordapp.com/attachments/1058519179973623888/1058695976132546570/that-was-pointless-1.png?ex=6853e8f6&is=68529776&hm=43223e59bdfd1e475618961f643442e7fafca92380c022414ae54005698f57cf&")

        embed.add_field(
            name=f"Bedwars {circle('green' if bedwars_ok else 'red')}",
            value=f"Wins: **{bedwars_wins}**\nStars: **{bedwars_stars}**\nFKDR: **{fkdr}**", inline=True)
        embed.add_field(
            name=f"Duels {circle('green' if duels_ok else 'red')}",
            value=f"Wins: **{duels_wins}**\nWLR: **{duels_wlr}**\nKills: **{duels_kills}**", inline=True)
        embed.add_field(
            name=f"Skywars {circle('green' if skywars_ok else 'red')}",
            value=f"Stars: **{skywars_stars}**\nWLR: **{skywars_wlr}**", inline=True)
        embed.add_field(
            name=f"Skyblock {circle('green' if skyblock_ok else 'red')}",
            value=f"Level: **{skyblock_level}**\nNetworth: **N/A**", inline=True)
        embed.add_field(
            name="Guild",
            value=f"Current Guild: **{guild_name}**\nGEXP: **{gexp}**", inline=True)
        embed.set_footer(text=f"Today at {datetime.now().strftime('%H:%M')} | Defeat Guild")

        await interaction.followup.send(embed=embed)

# --- /guildcheck Command ---

@bot.tree.command(name="guildcheck", description="Check all guild members against GEXP/Bedwars requirements")
@app_commands.describe(sort="Sort players by 'bedwars' or 'gexp'")
@is_staff()
async def guildcheck(interaction: discord.Interaction, sort: str = None):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        guild = await get_guild_by_name(session)
        if not guild:
            return await interaction.followup.send("❌ Failed to fetch guild data.")
        
        members = guild.get("members", [])
        results = []

        for m in members:
            uuid = m["uuid"]
            gexp = get_weekly_gexp(m.get("expHistory", {}))
            try:
                player = await get_player_data(session, uuid)
                if not player:
                    continue
                name = player.get("displayname", "Unknown")
                stats = player.get("stats", {})
                achievements = player.get("achievements", {})
                bedwars_wins = stats.get("Bedwars", {}).get("wins_bedwars", 0)
                bedwars_stars = achievements.get("bedwars_level", 0)
                bw_ok = get_bedwars_rating(bedwars_wins, bedwars_stars)
                gexp_ok = gexp >= 100000

                if bw_ok and gexp_ok:
                    status = "green"
                elif bw_ok or gexp_ok:
                    status = "yellow"
                else:
                    status = "red"

                results.append((circle(status), name, bedwars_wins, gexp))
            except Exception:
                continue

        if sort == "bedwars":
            results.sort(key=lambda x: x[2], reverse=True)
        elif sort == "gexp":
            results.sort(key=lambda x: x[3], reverse=True)

        embed = discord.Embed(
            title="Guild Requirement Check",
            description="Shows Bedwars Wins + Weekly GEXP requirement compliance.",
            color=discord.Color.blue()
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1058519179973623888/1058695976132546570/that-was-pointless-1.png?ex=6853e8f6&is=68529776&hm=43223e59bdfd1e475618961f643442e7fafca92380c022414ae54005698f57cf&")

        for emoji, name, wins, gexp in results:
            embed.add_field(
                name=f"{emoji} | {name}",
                value=f"**Bedwars Wins:** {wins}\n**GEXP:** {gexp}",
                inline=False
            )

        await interaction.followup.send(embed=embed)

bot.run(DISCORD_TOKEN)
