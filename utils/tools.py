import json
import os
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

# Check whether a value is an address
def is_address(value):
    if not isinstance(value, str):
        return False
    if len(value) == 42 and value.startswith("0x"):
        return True
    return False

def contract_creator(contract_addresses):
    contract_addresses = list(set(contract_addresses))
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
            if data["status"] != '0':
                for entry in data.get('result', []):
                    entry.pop('creationBytecode', None)  # Safely remove the field if it exists
                    results[entry['contractAddress']] = entry
        else:
            print(f"Error with batch {batch}: {response.status_code}, {response.text}")

        index += 5

    return results

def get_contract_info(contract_addresses, json_path='contract_info.json'):
    # Load existing data if file exists
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    exist_dict = 'contract_info.json'
    reading_dict = json_path == exist_dict
    if not reading_dict and os.path.exists(exist_dict):
        with open(exist_dict, 'r') as f:
            json_dict = json.load(f)
    else:
        json_dict = existing_data

    contract_addresses = [addr.lower() for addr in contract_addresses]  # Normalize
    cached_addresses = set(json_dict.keys())
    new_addresses = list(set(contract_addresses) - cached_addresses)

    # Query only new addresses
    if new_addresses:
        print(f"Querying {len(new_addresses)} new addresses from API...")
        new_data = contract_creator(new_addresses)
        existing_data.update(new_data)
        if not reading_dict:
            json_dict.update(new_data)
    else:
        print("All addresses found in local cache.")

    # Save back to JSON
    with open(json_path, 'w') as f:
        json.dump(existing_data, f, indent=2)

    if not reading_dict:
        with open(exist_dict, 'w') as f:
            json.dump(json_dict, f, indent=2)

    # Return only requested addresses
    return {addr: existing_data[addr] for addr in contract_addresses if addr in existing_data}

def brief_address_info(creation_info):
    if len(creation_info["contractFactory"]) != 0:
        code_created = False
    else:
        code_created = True
    return creation_info["contractCreator"], creation_info["timestamp"], code_created

def extract_contract_info(tx_data):
    contract_addresses = []
    output_tx_data = []
    for basic_info in tx_data:
        if not basic_info["to_is_eoa"]:
            contract_addresses.append(basic_info["to"])
    contract_creators = get_contract_info(contract_addresses)
    for basic_info in tx_data:
        if basic_info["to_is_eoa"] or basic_info["to"] == 'empty' or basic_info["to"] not in contract_creators:
            basic_info["to_creator"], basic_info["to_timestamp"], basic_info["code_created"] = "0x", 0, False
        else:
            basic_info["to_creator"], basic_info["to_timestamp"], basic_info["code_created"] \
                = brief_address_info(contract_creators[basic_info["to"]])
        output_tx_data.append(basic_info)
    return output_tx_data
