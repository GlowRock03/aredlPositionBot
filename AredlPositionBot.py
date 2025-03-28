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

CHANNEL_ID = 1300214311372984442

LAST_READ_FILE = "last_read.json"
LEVEL_DATA_FILE = "level_data.json"


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


# Load last read message ID
def load_last_read_message():
    try:
        with open(LAST_READ_FILE, "r") as f:
            return json.load(f).get("last_read", None)
    except FileNotFoundError:
        return None

# Save last read message ID
def save_last_read_message(message_id):
    with open(LAST_READ_FILE, "w") as f:
        json.dump({"last_read": message_id}, f)

# Load level data from JSON
def load_level_data():
    try:
        with open(LEVEL_DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save updated level data
def save_level_data(data):
    with open(LEVEL_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# Client Events
@client.event
async def on_ready():
    print(f"{client.user} has connected to Discord!")

    last_read_message = load_last_read_message()
    messages = []
    
    channel = client.get_channel(CHANNEL_ID)

    async for message in channel.history(limit=200, after=discord.Object(id=last_read_message) if last_read_message else None):
        messages.append(message)

    for message in messages:
        print(f"Processing message: \'{message.content}\'")
        #await process_message(message)
        #save_last_read_message(message.id)

        

    await asyncio.sleep(600)
    await client.close()
    
'''
# On Message Sent (user config)
@client.event
async def on_message(message):
    
    #or not message.channel.id == CHANNEL_ID:
    if message.author == client.user:
        return
'''
    

# Run Client
client.run(DISCORD_TOKEN)