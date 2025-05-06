import os
import argparse
from utils.get_rpc import EndpointPool
from utils.tx_detection import tx_detect
from utils.collect_basic_info import collect_info
from utils.collect_block import collect_block_all
from detect_utils.bytes_detection import detect_4bytes
from detect_utils.tools import load_json
import json
import time
import pandas as pd

chain_info = load_json("utils/chain_token_dict.json")  # Token info for all chains


def is_tx(tx_line: str):
    if isinstance(tx_line, str):
        if len(tx_line) == 66 and tx_line.startswith("0x"):
            return True
    return False


def main(block_number, chain, overwrite=False, llm_detect=False):
    time_dict = {}
    os.makedirs('result', exist_ok=True)

    folder_prefix = f'result/{block_number}_{chain}'
    # Create result directory if it doesn't exist
    if overwrite:
        print(f'Deleting result folder to overwrite {block_number} on {chain}')
        os.system(f'rm -rf {folder_prefix}')

    os.makedirs(folder_prefix, exist_ok=True)

    edpool = EndpointPool(chain)
    tx_list = collect_block_all(block_number, edpool)

    block_tx_info_start_time = time.time()
    # Collect transaction details
    tx_data = [collect_info(tx_hash, edpool) for tx_hash in tx_list]
    block_tx_info_end_time = time.time()
    time_dict['basic_info'] = block_tx_info_end_time - block_tx_info_start_time
    print(f"Block transaction info collection time: {block_tx_info_end_time - block_tx_info_start_time:.2f} seconds")

    # Convert to DataFrame and save to CSV
    if tx_data:
        if 'mev_bots' in chain_info[chain.lower()]:
            mev_bots = chain_info[chain.lower()]['mev_bots']
        else:
            mev_bots = []
        time_dict['tx_details'] = {}
        tx_df = pd.DataFrame(tx_data)
        suspicious_list = detect_4bytes(tx_df)
        csv_file = f"{folder_prefix}/transactions.csv"
        tx_df.to_csv(csv_file, index=False)
        for tx_hash in suspicious_list:
            # Extract basic information from the transaction DataFrame
            selected_tx = tx_df[tx_df['hash'] == tx_hash]
            if not selected_tx.empty:
                selected_tx_dict = selected_tx.to_dict(orient="records")[0]
            else:
                selected_tx_dict = None
            time_dict['tx_details'][tx_hash] = tx_detect(tx_hash, chain, block_number, folder_prefix,
                                                         selected_tx_dict, edpool, mev_bots, llm_detect)
        print(f"CSV file created: {csv_file}")
    else:
        print("No transactions found.")
    detection_end_time = time.time()
    time_dict['detection'] = detection_end_time - block_tx_info_end_time
    time_dict['total'] = detection_end_time - block_tx_info_start_time
    print(f"Total execution time: {detection_end_time - block_tx_info_end_time:.2f} seconds")
    with open(folder_prefix + f"/time_analysis.json", "w") as json_file:
        json.dump(time_dict, json_file, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_block_number", help="Block number for collection")
    parser.add_argument("chain", help="Ethereum block chain name")
    # use chatgpt to detect
    parser.add_argument("-llm", "--llm_detect", action="store_true", help="Use chatgpt to detect")
    # overwrite existing result
    parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite existing result")
    args = parser.parse_args()
    if "," in args.input_block_number:
        block_numbers = args.block_number.split(",")
        print(f'Collecting data for {len(block_numbers)} blocks.')
        for input_block_number in block_numbers:
            if isinstance(input_block_number, str) and input_block_number.isdigit():
                print(f'Collecting data for block {input_block_number}')
                main(input_block_number, args.chain, args.overwrite, args.llm_detect)
    else:
        input_block_number = args.input_block_number
        if isinstance(input_block_number, str) and input_block_number.isdigit():
            main(input_block_number, args.chain, args.overwrite, args.llm_detect)
        else:
            raise ValueError("not a transaction hash")