import json
import time
import requests

def load_json(filepath):
    """Utility function to load a JSON file safely."""
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)

# Get information of a transaction from the collected files
def collect_from_file(folder_prefix, filename):
    with open(folder_prefix + filename) as input_json:
        output_json = json.load(input_json)
    return output_json

def contract_creator(contract_addresses):
    url = "https://api.etherscan.io/v2/api"
    api_key = "VVAXBFG3KQAZHF4EGQ2FTTFES5ZA1WS3UZ"  # Replace with your API key

    results = {}
    index = 0

    while index < len(contract_addresses):
        # Get a batch of up to 5 addresses
        batch = contract_addresses[index:index + 5]
        address_param = ",".join(batch)

        params = {
            "chainid": 1,
            "module": "contract",
            "action": "getcontractcreation",
            "contractaddresses": address_param,
            "apikey": api_key
        }

        response = requests.get(url, params=params)

        if response.ok:
            data = response.json()
            for entry in data.get('result', []):
                results[entry['contractAddress']] = entry
        else:
            print(f"Error with batch {batch}: {response.status_code}, {response.text}")

        index += 5
        # Optional: Respect API rate limits
        time.sleep(0.2)

    return results