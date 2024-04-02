import pandas as pd
from web3 import Web3
import json
import os

w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
hash_event = pd.read_csv('event_dict.csv')
hash_dict = hash_event.set_index('hash')['event'].to_dict()


def convert(obj):
	if isinstance(obj, bytes):
		return obj.hex()
	elif isinstance(obj, list):
		return [convert(item) for item in obj]
	elif isinstance(obj, dict):
		return {convert(key): convert(value) for key, value in obj.items()}
	else:
		return obj

output_directory = 'event_json'
os.makedirs(output_directory, exist_ok=True)


def collect_event(raw_list):
	for transaction_hash in raw_list:
		transaction = w3.eth.get_transaction(transaction_hash)
		receipt = w3.eth.get_transaction_receipt(transaction_hash)
		logs = receipt['logs']
		logs_dicts = []
		for log_entry in logs:
			log_dict = {}
			for key, value in log_entry.items():
				log_dict[key] = convert(value)
			logs_dicts.append(log_dict)

		# Define the filename for the JSON file
		filename = f"{transaction_hash}_logs.json"

		# Save logs as JSON
		with open('event_json/' + filename, 'w') as file:
			json.dump(logs_dicts, file, indent=2)
