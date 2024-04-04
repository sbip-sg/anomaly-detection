from web3 import Web3
import requests
import json
import os

# Initialize Web3 instance with the RPC provider
w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))

# URL for the Infura API
url = 'https://mainnet.infura.io/v3/0377f17d56934a059be55f9d96fe5134'

# Headers for the HTTP request
headers = {'Content-Type': 'application/json'}

# Create a directory if it doesn't exist
output_directory = 'result/trace_json'
os.makedirs(output_directory, exist_ok=True)


# Function to collect transaction traces and save them as JSON files
def collect_trace(raw_list):
	for transaction_hash in raw_list:
		# Construct JSON-RPC request data
		data = {
			"jsonrpc": "2.0",
			"method": "trace_transaction",
			"params": [transaction_hash],
			"id": 1
		}

		# Send HTTP POST request to Infura API
		response = requests.post(url, json=data, headers=headers)

		if response.status_code == 200:
			# Extract result from response
			result = response.json().get("result", [])

			# Save the result as a JSON file
			filename = os.path.join(output_directory, f"trace_{transaction_hash}.json")
			with open(filename, 'w') as json_file:
				json.dump(result, json_file, indent=2)
