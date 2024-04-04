import pandas as pd
import requests
import json
import os
from os import listdir
from eth_abi import decode
import base64

# Read the CSV file containing event hash mappings
hash_df = pd.read_csv('dictionary/event_dict.csv')

# Convert DataFrame to dictionary for easy lookup
hash_dict = hash_df.set_index('hash')['event'].to_dict()

# Base URL for Etherface API
base_url = "https://api.etherface.io/v1/signatures/hash/all/"

# Function to decode input data based on its type
def decode_input(chunks):
    input_list = []
    for line in chunks:
        line = line[2:]  # Remove '0x' prefix
        count_of_zeros = len(line) - len(line.lstrip('0'))  # Count leading zeros
        if count_of_zeros >= 24 and count_of_zeros < 30:  # Address type
            input_list.append(decode(['address'], bytes.fromhex(line))[0])
        elif count_of_zeros >= 30 and count_of_zeros < 60:  # uint256 type
            input_list.append(decode(['uint256'], bytes.fromhex(line))[0])
    return input_list

# Function to convert bytes to base64 encoded string
def convert_bytes_to_string(obj):
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode('utf-8')
    raise TypeError("Object of type {} not serializable".format(type(obj)))

# Get list of JSON files in event_json directory
jsonlist = listdir('result/event_json')

# Function to decode event JSON files
def decode_event_json():
    json_file_path = 'result/decoded_event/'
    os.makedirs(json_file_path, exist_ok=True)
    for i in jsonlist:
        file = open('result/event_json/' + i)
        events = []
        tx = json.load(file)
        for event in tx:
            new_event = {}
            # Check if event is marked as removed
            if event['removed'] == True:
                new_event['removed'] = True
            # Check if topics exist
            if len(event["topics"]) != 0:
                func_hash = event["topics"][0][2:]  # Remove '0x' prefix
                # Check if func_hash exists in hash_dict
                if func_hash in hash_dict.keys():
                    new_event["eventname"] = hash_dict[func_hash]
                    new_event["topics"] = decode_input(event["topics"][1:])
                else:
                    # Get event name from Etherface API
                    api_url = f"{base_url}{func_hash}/1"
                    response = requests.get(api_url)
                    if response.status_code == 200:
                        result = response.json()
                        event_text = result['items'][0]['text']
                        new_event["eventname"] = event_text
                        hash_dict[func_hash] = event_text
                    else:
                        # Use func_hash as event name if API call fails
                        new_event["eventname"] = func_hash
                        hash_dict[func_hash] = func_hash
            # Decode topics and data
            new_event["topics"] = decode_input(event["topics"][1:])
            new_event["data"] = decode_input([event["data"]])
            new_event['address'] = event['address'].lower()

            events.append(new_event)
        # Write decoded events to JSON files
        with open(json_file_path + i, 'w') as jsonfile:
            json.dump(events, jsonfile, default=convert_bytes_to_string, indent=2)

