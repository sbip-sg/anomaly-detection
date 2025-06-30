import os
import argparse
from utils.get_rpc import EndpointPool
from utils.tx_detection import tx_detect
from utils.collect_basic_info import collect_info
from utils.collect_block import collect_block_all
from utils.tools import load_json, extract_contract_info
from detect_utils.bytes_detection import detect_4bytes
import json
import time
import pandas as pd

chain_info = load_json("utils/chain_token_dict.json")  # Token info for all chains


def is_tx(tx_line: str):
    if isinstance(tx_line, str):
        if len(tx_line) == 66 and tx_line.startswith("0x"):
            return True
    return False


def main(tx_hash, chain, overwrite=False, llm_detect=False):
    time_dict = {}
    os.makedirs('result', exist_ok=True)

    folder_prefix = f'result/{tx_hash}_{chain}/'
    # Create result directory if it doesn't exist
    if overwrite:
        print(f'Deleting result folder to overwrite {tx_hash} on {chain}')
        os.system(f'rm -rf {folder_prefix}')

    os.makedirs(folder_prefix, exist_ok=True)

    edpool = EndpointPool(chain)

    tx_info_start_time = time.time()
    # Collect transaction details
    tx_data, block_number = collect_info(tx_hash, edpool)
    tx_data = extract_contract_info([tx_data])[0]
    tx_info_end_time = time.time()
    time_dict['basic_info'] = tx_info_end_time - tx_info_start_time

    # Convert to DataFrame and save to CSV
    if tx_data:
        if 'mev_bots' in chain_info[chain.lower()]:
            mev_bots = chain_info[chain.lower()]['mev_bots']
        else:
            mev_bots = []
        time_dict['tx_details'] = {}
        time_dict['tx_details'][tx_hash] = tx_detect(tx_hash, chain, block_number, folder_prefix,
                                                         tx_data, edpool, mev_bots, llm_detect)
    else:
        print("No transactions found.")
    detection_end_time = time.time()
    time_dict['detection'] = detection_end_time - tx_info_end_time
    time_dict['total'] = detection_end_time - tx_info_start_time
    print(f"Total execution time: {detection_end_time - tx_info_end_time:.2f} seconds")
    with open(folder_prefix + f"/time_analysis.json", "w") as json_file:
        json.dump(time_dict, json_file, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_transaction_hash", help="Transaction hash for collection")
    parser.add_argument("chain", help="Ethereum block chain name")
    # use chatgpt to detect
    parser.add_argument("-llm", "--llm_detect", action="store_true", help="Use chatgpt to detect")
    # overwrite existing result
    parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite existing result")
    args = parser.parse_args()
    if "," in args.input_transaction_hash:
        transaction_hashes = args.input_block_number.split(",")
        print(f'Collecting data for {len(transaction_hashes)} txs.')
        for transaction_hash in transaction_hashes:
            if isinstance(transaction_hash, str):
                print(f'Collecting data for transaction {transaction_hash}')
                main(transaction_hash, args.chain, args.overwrite, args.llm_detect)
    else:
        transaction_hash = args.input_transaction_hash
        if isinstance(transaction_hash, str):
            main(transaction_hash, args.chain, args.overwrite, args.llm_detect)
        else:
            raise ValueError("not a transaction hash")