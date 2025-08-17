import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
HYPIXEL_API_KEY = os.getenv("HYPIXEL_API_KEY")
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID"))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="d!", intents=intents)

HYPIXEL_BASE = "https://api.hypixel.net"


# ------------- Helpers -----------------

async def fetch_json(session, url, params=None):
    async with session.get(url, params=params) as resp:
        return await resp.json()


def get_circle_color(bedwars_wins, gexp):
    meets_wins = bedwars_wins >= 2500
    meets_gexp = gexp >= 100000

    if meets_wins and meets_gexp:
        return ":green_circle:"
    elif meets_wins or meets_gexp:
        return ":yellow_circle:"
    else:
        return ":red_circle:"


async def get_guild_data(session):
    """Fetch guild members and stats."""
    url = f"{HYPIXEL_BASE}/guild"
    params = {"key": HYPIXEL_API_KEY, "name": "YOUR_GUILD_NAME"}
    data = await fetch_json(session, url, params)

    if not data.get("success"):
        return None

    return data["guild"]["members"]


async def get_player_stats(session, uuid):
    """Fetch player stats."""
    url = f"{HYPIXEL_BASE}/player"
    params = {"key": HYPIXEL_API_KEY, "uuid": uuid}
    data = await fetch_json(session, url, params)

    if not data.get("success") or not data.get("player"):
        return None

    player = data["player"]
    bedwars_wins = player.get("stats", {}).get("Bedwars", {}).get("wins_bedwars", 0)
    gexp = player.get("gexp", 0)  
    return bedwars_wins, gexp, player.get("displayname", "Unknown")


# ------------- Commands -----------------

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)


def is_staff():
    async def predicate(interaction: discord.Interaction):
        staff_role = discord.utils.get(interaction.guild.roles, id=STAFF_ROLE_ID)
        if staff_role in interaction.user.roles:
            return True
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)


@bot.tree.command(name="guildcheck", description="Check all guild members against requirements")
@app_commands.describe(sort="Sort players by 'bedwars' or 'gexp'")
@is_staff()
async def guildcheck(interaction: discord.Interaction, sort: str = None):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        guild_members = await get_guild_data(session)
        if not guild_members:
            return await interaction.followup.send("Failed to fetch guild data.")

        results = []
        for member in guild_members:
            uuid = member["uuid"]
            gexp = member.get("expHistory", {}).get("0", 0)  
            player_stats = await get_player_stats(session, uuid)
            if player_stats:
                bedwars_wins, _, name = player_stats
                circle = get_circle_color(bedwars_wins, gexp)
                results.append((circle, name, bedwars_wins, gexp))

        if sort == "bedwars":
            results.sort(key=lambda x: x[2], reverse=True)
        elif sort == "gexp":
            results.sort(key=lambda x: x[3], reverse=True)

        embed = discord.Embed(
            title="Guild Requirement Check",
            description="Bedwars Wins ≥ 2500 | Weekly GEXP ≥ 100k",
            color=discord.Color.blue()
        )
        for circle, name, wins, gexp in results:
            embed.add_field(
                name=f"{circle} | {name}",
                value=f"**Bedwars Wins:** {wins}\n**GEXP:** {gexp}",
                inline=False
            )

        await interaction.followup.send(embed=embed)


@bot.tree.command(name="reqcheck", description="Check requirements for a specific player")
@app_commands.describe(username="Minecraft username")
@is_staff()
async def reqcheck(interaction: discord.Interaction, username: str):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        
        url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
        mojang_data = await fetch_json(session, url)
        if "id" not in mojang_data:
            return await interaction.followup.send("Could not find that player.")

        uuid = mojang_data["id"]
        player_stats = await get_player_stats(session, uuid)
        if not player_stats:
            return await interaction.followup.send("Failed to fetch player stats.")

        bedwars_wins, gexp, name = player_stats
        circle = get_circle_color(bedwars_wins, gexp)

        embed = discord.Embed(
            title="Defeat Requirement Check",
            description=f"Below is the requirement check for **{name}**!",
            color=discord.Color.purple()
        )
        embed.add_field(
            name=f"{circle} {name}",
            value=f"**Bedwars Wins:** {bedwars_wins}\n**GEXP:** {gexp}",
            inline=False
        )

        await interaction.followup.send(embed=embed)


bot.run(TOKEN)
