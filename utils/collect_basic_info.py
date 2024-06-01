import pandas as pd
from web3 import Web3
import os
import json
from web3.middleware import geth_poa_middleware
from datetime import datetime

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
	if type(raw_list) == tuple:
		raw_list = [raw_list]
	# Define columns for the new DataFrame
	new_dataframe_columns = ['hash', 'value', 'from', 'to', 'gasUsed', 'timestamp']
	# Create an empty DataFrame with defined columns
	new_dataframe = pd.DataFrame(columns=new_dataframe_columns)

	timestamps_dict = {}

	# Loop through each transaction hash in the input list
	for transaction_hash, rpc in raw_list:
		# Initialize Web3 instance with the RPC provider
		w3 = Web3(Web3.HTTPProvider(rpc))
		w3.middleware_onion.inject(geth_poa_middleware, layer=0)
		# Get transaction details
		transaction = w3.eth.get_transaction(transaction_hash)
		# Get transaction receipt
		receipt = w3.eth.get_transaction_receipt(transaction_hash)
		try:
			timestamp = w3.eth.get_block(transaction['blockNumber'])['timestamp']
			timestamps_dict[transaction_hash] = timestamp
		except Exception as e:
			print(e)
			raise ValueError("Can not find timestamp because the block is not recorded.")


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

	# Return the DataFrame containing transaction information
	return new_dataframe, timestamps_dict
