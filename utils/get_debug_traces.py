import requests
from requests.exceptions import HTTPError
import json
import os

# Headers for the HTTP request
headers = {'Content-Type': 'application/json'}

# Function to collect transaction traces and save them as JSON files
def collect_debug_trace(transaction_hash, edpool, folder_prefix="result"):
    # Create a directory if it doesn't exist
    output_directory = folder_prefix + '/trace_json'
    os.makedirs(output_directory, exist_ok=True)
    filename = os.path.join(output_directory, f"trace_{transaction_hash}.json")
    rpc = edpool.endpoint_by_chain()
    data = {
            "jsonrpc": "2.0",
            "method": "trace_transaction",
            "params": [transaction_hash],
            "id": 1
        }

    # Send HTTP POST request to Infura API
    while True:
        try:
            response = requests.post(rpc, json=data, headers=headers)

            if response.status_code == 200:
                # Extract result from response
                result = response.json().get("result", [])

                with open(filename, 'w') as json_file:
                    json.dump(result, json_file, indent=2)
                print('trace_finished', transaction_hash)
                break

        except HTTPError as e:
            # Handle HTTP errors
            rpc = edpool.mark_endpoint_broken(rpc)
            print(f'Error processing tracing: {e}\n retry ... ')

        except Exception as e:
            # Handle other unexpected exceptions
            raise RuntimeError(f"An unexpected error occurred: {e}")
