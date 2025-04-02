import json
import requests

# API endpoint
API_URL = "https://api.aredl.net/api/aredl/levels"

# Fetch data from the API
response = requests.get(API_URL)

# Check if the request was successful
if response.status_code == 200:
    data = response.json()  # Parse JSON response

    # Transform data to match the required format
    levels = []
    for level in data:
        level_entry = {
            "position": level["position"],
            "name": level["name"].lower()
        }
        # Add "legacy" only if it exists in the API response
        if "legacy" in level:
            level_entry["legacy"] = level["legacy"]
        else:
            level_entry["legacy"] = False

        levels.append(level_entry)

    # Save to a JSON file
    with open("data/level_data.json", "w", encoding="utf-8") as json_file:
        json.dump(levels, json_file, indent=4, ensure_ascii=False)

    print("Data successfully saved to aredl_levels.json")
else:
    print(f"Failed to fetch data. HTTP Status Code: {response.status_code}")