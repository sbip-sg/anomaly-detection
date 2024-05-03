import pandas as pd
from web3 import Web3
import os
import json
from web3.middleware import geth_poa_middleware
from datetime import datetime

# Initialize Web3 instance with the RPC provider
w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

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



# Function to collect transaction information and return as a DataFrame
def collectinfo(raw_list, folder_prefix="result"):
	# Define output directory for JSON files
	output_directory = folder_prefix+'/event_json'
	os.makedirs(output_directory, exist_ok=True)
	if type(raw_list) == str:
		raw_list = [raw_list]
	# Define columns for the new DataFrame
	new_dataframe_columns = ['hash', 'value', 'from', 'to', 'gasUsed', 'timestamp']
	# Create an empty DataFrame with defined columns
	new_dataframe = pd.DataFrame(columns=new_dataframe_columns)

	timestamps_dict = {}

	# Loop through each transaction hash in the input list
	for transaction_hash in raw_list:
		# Get transaction details
		transaction = w3.eth.get_transaction(transaction_hash)
		# Get transaction receipt
		receipt = w3.eth.get_transaction_receipt(transaction_hash)
		try:
			timestamp = w3.eth.get_block(transaction['blockNumber'])['timestamp']
			timestamps_dict[transaction_hash] = timestamp
		except Exception as e:
			print('Can not find time Stamp due to the block is not is not recorded.')
			current_timestamp = datetime.now().timestamp()
			timestamp = None
			timestamps_dict[transaction_hash] = current_timestamp - 3600


		# Extract sender and recipient addresses, converting to lowercase for consistency
		sender = transaction['from'].lower()
		if transaction['to']:
			recipient = transaction['to'].lower()
		else:
			recipient = 'empty'

		# Construct dictionary containing transaction data
		transaction_data = {
			'hash': transaction_hash,
			'value': transaction['value'] / 1e18,  # Convert value from Wei to Ether
			'from': sender,
			'to': recipient,
			'gasUsed': receipt['gasUsed'],  # Get gas used from transaction receipt
			'timestamp': timestamp
		}

		# Append transaction data to the DataFrame
		new_dataframe.loc[len(new_dataframe)] = transaction_data

		logs = receipt['logs']
		logs_dicts = []
		# Convert logs to dictionaries and append to a list
		for log_entry in logs:
			log_dict = {}
			for key, value in log_entry.items():
				log_dict[key] = convert(value)
			logs_dicts.append(log_dict)

		# Define the filename for the JSON file
		filename = f"events_{transaction_hash}.json"

		# Save logs as JSON
		with open(folder_prefix+'/event_json/' + filename, 'w') as file:
			json.dump(logs_dicts, file, indent=2)

	# Return the DataFrame containing transaction information
	return new_dataframe, timestamps_dict
