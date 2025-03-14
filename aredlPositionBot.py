import os
import json
import discord
import asyncio
from google.oauth2 import service_account
from dotenv import load_dotenv

# Setup Client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Load Secret Keys
if not os.getenv("GITHUB_ACTIONS"):
    load_dotenv("secrets/.env")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("Missing \'DISCORD_TOKEN\' environment variable")

if not os.getenv("GITHUB_ACTIONS"):
    with open("secrets/aredlpositionbot-credentials.json") as json_file:
        credentials_info = json.load(json_file)
else:
    GOOGLE_CLOUD_KEY = os.getenv("GOOGLE_CLOUD_KEY")
    if not GOOGLE_CLOUD_KEY:
        raise ValueError("Missing 'GOOGLE_CLOUD_KEY' environment variable")
    credentials_info = json.loads(GOOGLE_CLOUD_KEY)
credentials = service_account.Credentials.from_service_account_info(credentials_info)

# Client Events
@client.event
async def on_ready():
    print(f"{client.user} has connected to Discord!")

    await asyncio.sleep(600)
    await client.close()

# Run Client
client.run(DISCORD_TOKEN)