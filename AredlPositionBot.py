import os
import json
import discord
import asyncio
import re
import gspread
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv



# Setup Client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

CHANNEL_ID = 1300214311372984442
global queue
queue = []

LAST_READ_FILE = "data/last_read.json"
LEVEL_DATA_FILE = "data/level_data.json"
USER_DATA_FILE = "data/user_config.json"

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
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
gc = gspread.authorize(credentials)


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

# Load the existing user config or create a new one if it doesn't exist
def load_user_configs():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Save the user configs to the file
def save_user_configs(user_configs):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(user_configs, f, indent=4)


def queue_changes(message):

    # Clean the message content and prepare for processing
    raw_content = message.content.replace("*", "")
    
    # Split by newlines or dashes, then strip leading dashes and spaces from each entry
    entries = [entry.lstrip("- ").strip() for entry in raw_content.splitlines()]

    for content in entries:
        # Clean up formatting and prepare content for matching
        content = re.sub(r"\*\*(.+?)\*\*", r"\1", content)

        # Regex patterns for each type of change
        move_pattern = r"(.+?) has been (raised|lowered) from #(\d+) to #(\d+)"
        place_pattern = r"(.+?) has been placed at #(\d+)"
        swap_pattern = r"(.+?) and (.+?) have been swapped, with (.+?) (now|sitting|now sitting) (above|below) at #(\d+)"

        # Enqueue each type of match
        for match in re.finditer(move_pattern, content):
            level_name = match.group(1).strip()
            move_type = match.group(2)  # "raised" or "lowered"
            old_position = match.group(3).strip()
            new_position = match.group(4).strip()
            queue.append(("move", level_name, move_type, old_position, new_position))

        for match in re.finditer(place_pattern, content):
            level_name = match.group(1).strip()
            position = match.group(2).strip()
            queue.append(("place", level_name, position))

        for match in re.finditer(swap_pattern, content):
            level1 = match.group(1).strip()
            level2 = match.group(2).strip()
            marking_level = match.group(3).strip()  # The level taking the specific position
            position_direction = match.group(5).strip()  # "above" or "below"
            new_position = int(match.group(6).strip())
            queue.append(("swap", level1, level2, marking_level, position_direction, new_position))

def process_queue():
    
    # Load the existing data
    with open(LEVEL_DATA_FILE, "r") as f:
        level_data = json.load(f)

    # Convert list to a dictionary for easier access
    level_dict = {level["name"]: level for level in level_data}

    for item in queue:
        action = item[0]

        if action == "move":
            level_name, move_type, old_position, new_position = item[1:]
            old_position, new_position = int(old_position), int(new_position)

            if level_name in level_dict:
                level_dict[level_name]["position"] = new_position

            # Shift positions for other levels accordingly
            for level in level_dict.values():
                pos = level["position"]
                if new_position < pos < old_position:
                    level["position"] += 1
                elif old_position < pos < new_position:
                    level["position"] -= 1

        elif action == "place":
            level_name, position = item[1:]
            position = int(position)

            if level_name not in level_dict:
                level_dict[level_name] = {"name": level_name, "position": position, "legacy": False}
            else:
                level_dict[level_name]["position"] = position

            # Shift other levels down if needed
            for level in level_dict.values():
                if level["position"] >= position and level["name"] != level_name:
                    level["position"] += 1

        elif action == "swap":
            level1, level2, marking_level, position_direction, new_position = item[1:]
            new_position = int(new_position)

            if marking_level == level1:
                pos1, pos2 = new_position, new_position + 1 if position_direction == "above" else new_position - 1
            else:
                pos1, pos2 = new_position - 1 if position_direction == "above" else new_position, new_position

            if level1 in level_dict and level2 in level_dict:
                level_dict[level1]["position"] = pos1
                level_dict[level2]["position"] = pos2

    # Convert back to sorted list
    sorted_levels = sorted(level_dict.values(), key=lambda x: x["position"])

    # Save back to JSON
    with open(LEVEL_DATA_FILE, "w") as f:
        json.dump(sorted_levels, f, indent=4)

    print("Level data updated successfully!")

def update_google_sheets():
    # Load user configs
    with open(USER_DATA_FILE, "r") as f:
        user_configs = json.load(f)

    # Load level data
    with open(LEVEL_DATA_FILE, "r") as f:
        level_data = json.load(f)

    # Convert level data into a dictionary for quick lookup
    level_positions = {level["name"]: {"position": level["position"], "legacy": level.get("legacy", False)} for level in level_data}

    # Iterate through each user's configuration
    for user_id, config in user_configs.items():
        try:
            sheet_name = config["sheetName"]
            page_name = config["sheetPage"]  # Now using the name of the sheet instead of an index
            level_name_column = config["levelNameColumn"]
            position_column = config["positionColumn"]

            # Open the Google Sheet and get the specific sheet by name
            sheet = gc.open(sheet_name).worksheet(page_name)

            # Fetch all level names from the configured column
            level_names = sheet.col_values(ord(level_name_column) - ord('A') + 1)  # Convert column letter to index

            # Prepare batch update data
            updates = []
            for i, level_name in enumerate(level_names, start=1):  # Google Sheets row index starts at 1
                if level_name in level_positions:
                    position_data = level_positions[level_name]
                    new_value = "Legacy" if position_data["legacy"] else position_data["position"]
                    
                    # Add to batch update list
                    updates.append({
                        "range": f"{position_column}{i}",
                        "values": [[new_value]]
                    })

            # Execute batch update if there are changes
            if updates:
                sheet.batch_update(updates)
                print(f"Updated {len(updates)} cells in batch for user {user_id}")
            else:
                print(f"No updates needed for user {user_id}")

        except Exception as e:
            print(f"Error updating sheet for user {user_id}: {str(e)}")

# Client Events
@client.event
async def on_ready():
    print(f"{client.user} has connected to Discord!")

    last_read_message = load_last_read_message()
    messages = []
    channel = client.get_channel(CHANNEL_ID)
    foundFlag = False

    async for message in channel.history(limit=200, after=discord.Object(id=last_read_message) if last_read_message else None):
        messages.append(message)
        foundFlag = True

    for message in messages:
        print(f"Processing message: \'{message.content}\'")
        queue_changes(message)
        save_last_read_message(message.id)

    if not foundFlag:
        print("No new messages found!")
    else:
        print("\n\nProcessing Message Queue")
        process_queue()

    print("\n\nUpdating Google Sheets...")
    update_google_sheets()
    print("Google Sheets update complete!")
    


    await asyncio.sleep(600)
    await client.close()


# Command to process user configurations
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!config"):
        try:
            _, setting, value = message.content.split(" ", 2)
            user_id = str(message.author.id)
            user_configs = load_user_configs()

            # Check if the user exists in the config file; if not, add them
            if user_id not in user_configs:
                user_configs[user_id] = {}

            # Validate the settings and values, and update the config
            if setting == "sheetName":
                user_configs[user_id]["sheetName"] = value
            elif setting == "sheetPage":
                user_configs[user_id]["sheetPage"] = int(value)
            elif setting == "levelNameColumn":
                user_configs[user_id]["levelNameColumn"] = value
            elif setting == "positionColumn":
                user_configs[user_id]["positionColumn"] = value
            else:
                await message.channel.send(f"Invalid setting: {setting}")
                return

            # Save the updated configurations
            save_user_configs(user_configs)
            await message.channel.send(f"Configuration updated for user {message.author.name}.")

        except ValueError:
            await message.channel.send("Invalid command format. Please use: !config <SETTING> <VALUE>")
        except Exception as e:
            await message.channel.send(f"Error: {str(e)}")
    

    if message.content.startswith("!requirements"):
        await message.channel.send(f"1. Your spreadsheet must be a Google Sheet\n2. You must add the bot\'s email as an editor to your spreadsheet: aredl-position-bot-service@aredlpositionbot.iam.gserviceaccount.com\n3. You must have your spreadsheet setup in columns (for the headers) and each level should be on its own row below the headers\n4. You must have a Level Name column (the header can be named to something else) and a Level Position column (the header can be named to something else too)\n5. In the Level Name Column, each level\'s name HAS TO EXACTLY MATCH the name on the AREDL (adderall) website\n6. In discord you must run ALL 4 !config commands (see !setup for instructions)")
    
    if message.content.startswith("!setup"):
        await message.channel.send(f"Ensure you have followed the requirements from !requirements before starting:\n1. Contact the developer (@glowrock) on discord to start the bot for you\n2. Once the bot is running, run each of the !config commands found in !help\n3. If you have followed the steps correctly, your Google Sheet will now update daily with all of the AREDL (adderall) updates")
        
    if message.content.startswith("!help"):
        await message.channel.send(f"All commands:\n!config sheetName <The name of your google sheet>\n!config sheetPage <The name of the sheet you have your aredl positions on>\n!config levelNameColumn <The column of the level names>\n!config positionColumn <The column of the level positions>\n!requirements\n!setup\n!help")

# Run Client
client.run(DISCORD_TOKEN)