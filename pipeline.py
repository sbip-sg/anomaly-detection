import os
import argparse
from utils.collect_basic_info import collectinfo
from utils.get_traces import collect_trace
from utils.decode_trace import decode_trace_json
from utils.other_balance import collect_token
from utils.eth_balance import collect_eth

rpc_endpoints = {
    "mainnet": "https://rpc.ankr.com/eth",
    "optimism": "https://opt-mainnet.g.alchemy.com/v2/demo",
    "fantom": "https://rpc.ankr.com/fantom",
    "arbitrum": "https://rpc.ankr.com/arbitrum",
    "bsc": "https://rpc.ankr.com/bsc",
    "moonriver": "https://moonriver.public.blastapi.io",
    "gnosis": "https://rpc.ankr.com/gnosis",
    "Avalanche": "https://rpc.ankr.com/avalanche",
    "polygon": "https://rpc.ankr.com/polygon",
    "celo": "https://rpc.ankr.com/celo",
    "Base": "https://developer-access-mainnet.base.org"
}

def main(tx_hash, chain, overwrite=False):
	# Create result directory if it doesn't exist
	os.makedirs('result', exist_ok=True)
	folder_prefix = f'result/{tx_hash}_eth'
	os.makedirs(folder_prefix, exist_ok=True)
	if (not overwrite) and os.path.exists(f'{folder_prefix}/basic_info.json'):
		print(f"Result for {tx_hash} already exists. Use -o to overwrite.")
		return
	# Collect basic information

	raw = (tx_hash, rpc_endpoints[chain])
	basic_info, time_stamp_dict = collectinfo(raw, folder_prefix)
	# basic_info.to_csv('result/basic_info.csv')
	basic_info.to_json(folder_prefix + '/basic_info.json', orient='records', lines=True)

	# Collect traces
	collect_trace(raw,folder_prefix)

	# Decode trace JSON
	decode_trace_json(folder_prefix)

	# Collect token balances
	#total_dict, flow = collect_token(time_stamp_dict, folder_prefix)
	# Collect ETH balances
	#collect_eth(total_dict, time_stamp_dict, flow, folder_prefix)

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("tx_hash", help="Path to the input file")
	parser.add_argument("chain", help="Transaction chain name")
	# overwrite existing result
	parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite existing result")
	args = parser.parse_args()
	main(args.tx_hash, args.chain, args.overwrite)