import os
import discord
import asyncio

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    raise ValueError("Missing DISCORD_TOKEN environment variable")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"{client.user} has connected to Discord!")

    await asyncio.sleep(600)
    await client.close()

client.run(DISCORD_TOKEN)