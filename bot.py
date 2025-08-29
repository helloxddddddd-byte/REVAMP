import discord
from discord.ext import tasks
import aiohttp
import asyncio
import random
import os

# -------------------------
# CONFIG
# -------------------------
TOKEN = os.getenv("DISCORD_TOKEN")  # Load from secret
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))  # Optional: also as secret
PLACE_ID = int(os.getenv("PLACE_ID", 0))      # Optional: also as secret

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Get visits using UniverseId API
async def get_visits():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://apis.roblox.com/universes/v1/places/{PLACE_ID}/universe") as r:
            if r.status != 200:
                return None
            universe_data = await r.json()
            universe_id = universe_data.get("universeId")

        if not universe_id:
            return None

        async with session.get(f"https://games.roblox.com/v1/games?universeIds={universe_id}") as r:
            if r.status != 200:
                return None
            data = await r.json()
            if "data" in data and len(data["data"]) > 0:
                return data["data"][0].get("visits", 0)

    return None

# Get active players by summing all server player counts
async def get_active_players():
    url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public?limit=100"
    total_players = 0

    async with aiohttp.ClientSession() as session:
        cursor = None
        while True:
            fetch_url = url + (f"&cursor={cursor}" if cursor else "")
            async with session.get(fetch_url) as r:
                if r.status != 200:
                    break
                data = await r.json()

                for server in data.get("data", []):
                    total_players += server.get("playing", 0)

                cursor = data.get("nextPageCursor")
                if not cursor:
                    break

    return total_players

# Task loop every 65s
@tasks.loop(seconds=65)
async def send_game_data():
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        return

    # Step 1: wait 3s before collecting active players (fresh data)
    await asyncio.sleep(3)
    active = await get_active_players()
    visits = await get_visits()

    if visits is not None:
        milestone = visits + random.randint(100, 150)
        msg = (
            "--------------------------------------------------\n"
            f"👤🎮 Active players: {active}\n"
            "--------------------------------------------------\n"
            f"👥 Visits: {visits:,}\n"
            f"🎯 Next milestone: {visits:,}/{milestone:,}\n"
            "--------------------------------------------------"
        )
        await channel.send(msg)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    send_game_data.start()

client.run(TOKEN)
