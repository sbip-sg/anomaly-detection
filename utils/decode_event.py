import json
import os
from os import listdir
from eth_abi import decode
import base64
from lookup_event import get_event_db_signature

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

# Function to decode event JSON files
def decode_event_json(folder_prefix="result"):
    # Get list of JSON files in event_json directory
    jsonlist = listdir(folder_prefix + '/event_json')
    json_file_path = folder_prefix + '/decoded_event/'
    os.makedirs(json_file_path, exist_ok=True)
    for i in jsonlist:
        file = open(folder_prefix + '/event_json/' + i)
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
                event_name= get_event_db_signature(func_hash)
                if event_name:
                    new_event["eventname"] = event_name
                else:
                    new_event["eventname"] = func_hash
            # Decode topics and data
            new_event["topics"] = decode_input(event["topics"][1:])
            new_event["data"] = decode_input([event["data"]])
            new_event['address'] = event['address'].lower()

            events.append(new_event)
        # Write decoded events to JSON files
        with open(json_file_path + i, 'w') as jsonfile:
            json.dump(events, jsonfile, default=convert_bytes_to_string, indent=2)
        print('decode_event_finished', i)

