# Function to collect transaction traces and save them as JSON files
import subprocess
import json
import os
from utils.find_rpc import endpoint_by_chain, handle_error

cast_bin = os.environ.get('CAST_BIN', 'cast')


def cast_run(rpc_url, txhash, output):
        print('Foundry Start')
        r = subprocess.run([cast_bin, 'run', '-q', '-r', rpc_url, txhash, '--output', output], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, text=True, check=True)
        print('Foundry End')
        r.check_returncode()
        return json.load(open(output))

def collect_trace(transaction_hash, chain, endpoint_idx, folder_prefix="result"):
        # Create a directory if it doesn't exist
        output_directory = folder_prefix + '/trace_json'
        os.makedirs(output_directory, exist_ok=True)
        filename = os.path.join(output_directory, f"trace_{transaction_hash}.json")
        rpc, endpoint_idx = endpoint_by_chain(chain, endpoint_idx)
        while True:
                try:
                        # Initialize Web3 instance with the RPC provider
                        cast_run(rpc, transaction_hash, filename)
                        break
                except Exception as e:
                        endpoint_idx = handle_error(chain, endpoint_idx)
                        rpc, endpoint_idx = endpoint_by_chain(chain, endpoint_idx)
                        print(f'Error processing request: {e}\n retry ... ')
                print('trace_finished', transaction_hash)
        return endpoint_idx
