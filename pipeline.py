import os
import argparse
from utils.collect_basic_info import collectinfo
from utils.get_traces import collect_trace
from utils.decode_event import decode_event_json
from utils.decode_trace import decode_trace_json
from utils.other_balance import collect_token
from utils.eth_balance import collect_eth


def main(tx_hash, overwrite=False):
	# Create result directory if it doesn't exist
	os.makedirs('result', exist_ok=True)
	folder_prefix = f'result/{tx_hash}_eth'
	os.makedirs(folder_prefix, exist_ok=True)
	if (not overwrite) and os.path.exists(f'{folder_prefix}/basic_info.json'):
		print(f"Result for {tx_hash} already exists. Use -o to overwrite.")
		return
	# Collect basic information
	basic_info = collectinfo(tx_hash, folder_prefix)
	# basic_info.to_csv('result/basic_info.csv')
	basic_info.to_json(folder_prefix + '/basic_info.json', orient='records', lines=True)

	# Collect traces
	collect_trace(tx_hash,folder_prefix)

	# Decode event JSON
	decode_event_json(folder_prefix)

	# Decode trace JSON
	decode_trace_json(folder_prefix)

	# Collect token balances
	collect_token(folder_prefix)
	# Collect ETH balances
	collect_eth(folder_prefix)

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("tx_hash", help="Path to the input file")
	# overwrite existing result
	parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite existing result")
	args = parser.parse_args()
	main(args.tx_hash, args.overwrite)