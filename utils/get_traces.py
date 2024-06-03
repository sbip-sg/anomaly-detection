
# Function to collect transaction traces and save them as JSON files
import subprocess
import json
import os

cast_bin = os.environ.get('CAST_BIN', 'cast')


def cast_run(rpc_url, txhash, output):
	subprocess.run([cast_bin, 'run', '-r', rpc_url, txhash, '--output', output], stdout=subprocess.DEVNULL,
		                        stderr=subprocess.DEVNULL, text=True, check=True)
	return json.load(open(output))

def collect_trace(raw_list, folder_prefix="result"):
	# Create a directory if it doesn't exist
	output_directory = folder_prefix + '/trace_json'
	os.makedirs(output_directory, exist_ok=True)
	if type(raw_list) == tuple:
		raw_list = [raw_list]
	for transaction_hash, rpc in raw_list:
		# Construct JSON-RPC request data
		filename = os.path.join(output_directory, f"trace_{transaction_hash}.json")
		cast_run(rpc, transaction_hash, filename)
		print('trace_finished', transaction_hash)