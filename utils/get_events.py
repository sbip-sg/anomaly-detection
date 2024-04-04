import pandas as pd
from web3 import Web3
import json
import os

# Initialize Web3 instance with the RPC provider
w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))

# Load event dictionary from CSV file into DataFrame
hash_event = pd.read_csv('dictionary/event_dict.csv')

# Convert DataFrame to dictionary for easy lookup
hash_dict = hash_event.set_index('hash')['event'].to_dict()


# Function to recursively convert bytes to hexadecimal, lists, and dictionaries
def convert(obj):
	if isinstance(obj, bytes):
		return obj.hex()
	elif isinstance(obj, list):
		return [convert(item) for item in obj]
	elif isinstance(obj, dict):
		return {convert(key): convert(value) for key, value in obj.items()}
	else:
		return obj


# Define output directory for JSON files
output_directory = 'result/event_json'
os.makedirs(output_directory, exist_ok=True)


# Function to collect event logs and save them as JSON files
def collect_event(raw_list):
	for transaction_hash in raw_list:
		# Get transaction receipt
		receipt = w3.eth.get_transaction_receipt(transaction_hash)
		# Get logs from the transaction receipt
		logs = receipt['logs']
		logs_dicts = []
		# Convert logs to dictionaries and append to a list
		for log_entry in logs:
			log_dict = {}
			for key, value in log_entry.items():
				log_dict[key] = convert(value)
			logs_dicts.append(log_dict)

		# Define the filename for the JSON file
		filename = f"{transaction_hash}_logs.json"

		# Save logs as JSON
		with open('result/event_json/' + filename, 'w') as file:
			json.dump(logs_dicts, file, indent=2)
