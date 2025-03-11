import os
import argparse
from utils.collect_basic_info import collect_info
from utils.get_traces import collect_trace
from utils.decode_trace import decode_trace_json
from utils.token_info import collect_token
from utils.get_rpc import EndpointPool
from utils.generate_output import generate_output
from utils.collect_block import collect_block_all
from detect_utils.detect_all import rule_based_detection
from detect_utils.chatgpt_detect import chatgpt_detect
import json
import pandas as pd

# Get transaction information by hash
def collect_tx(tx_hash, chain, overwrite=False, use_llm=False):
    folder_prefix = f'result/{tx_hash}_{chain}'
    # Create result directory if it doesn't exist
    if overwrite:
        print(f'Deleting result folder to overwrite {tx_hash} on {chain}')
        os.system(f'rm -rf {folder_prefix}')

    os.makedirs('result', exist_ok=True)

    os.makedirs(folder_prefix, exist_ok=True)

    edpool = EndpointPool(chain)
    # Collect basic information
    basic_info = collect_info(tx_hash, edpool)

    with open(folder_prefix + '/basic_info.json', 'w') as json_file:
        json.dump(basic_info, json_file, indent=2)

    # Collect traces (raw invocation tree)
    collect_trace(tx_hash, edpool, folder_prefix)

    # Decode trace JSON and extract information from invocation tree
    decode_trace_json(folder_prefix)

    # According to the decoded invocation tree, get token flow and balance changes.
    main_token = collect_token(tx_hash, chain, basic_info['from'], basic_info['to'], basic_info['blocknumber'], edpool, folder_prefix)

    detection_result, reason, la_tx = rule_based_detection(tx_hash, folder_prefix)

    basic_info['detection_result'] = detection_result
    basic_info['reason'] = reason
    basic_info['large_amount'] = la_tx # 63k USD, the hard margin of linear SVM

    # Save basic information
    with open(folder_prefix + '/basic_info.json', 'w') as json_file:
        json.dump(basic_info, json_file, indent=2)

    generate_output(tx_hash, chain, folder_prefix, main_token)

    # if use_chatgpt and detection_result:
    if use_llm:
        try:
            chatgpt_detect(tx_hash, folder_prefix)
            # deepseekv3_detect(tx_hash, folder_prefix)
        except Exception as e:
            print('Chatgpt Error:', e)

def is_tx(tx_line: str):
    if isinstance(tx_line, str):
        if len(tx_line) == 66 and tx_line.startswith("0x"):
            return True
    return False

def main(block_number, chain, overwrite=False):
    os.makedirs('result', exist_ok=True)

    folder_prefix = f'result/{block_number}_{chain}'
    # Create result directory if it doesn't exist
    if overwrite:
        print(f'Deleting result folder to overwrite {block_number} on {chain}')
        os.system(f'rm -rf {folder_prefix}')

    os.makedirs(folder_prefix, exist_ok=True)

    edpool = EndpointPool(chain)
    tx_list = collect_block_all(block_number, edpool)

    # Collect transaction details
    tx_data = [collect_info(tx_hash, edpool) for tx_hash in tx_list]

    # Convert to DataFrame and save to CSV
    if tx_data:
        df = pd.DataFrame(tx_data)
        csv_file = f"{folder_prefix}/transactions.csv"
        df.to_csv(csv_file, index=False)

        print(f"CSV file created: {csv_file}")
    else:
        print("No transactions found.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("block_number", help="Ethereum block number")
    parser.add_argument("chain", help="Ethereum block chain name")
    # use chatgpt to detect
    parser.add_argument("-llm", "--llm_detect", action="store_true", help="Use chatgpt to detect")
    # overwrite existing result
    parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite existing result")
    args = parser.parse_args()
    if "," in args.block_number:
        block_numbers = args.tx_hash.split(",")
        print(f'Collecting data for {len(block_numbers)} transactions')
        for block_number in block_numbers:
            if isinstance(block_number, int):
                print(f'Collecting data for block {block_number}')
                main(block_number, args.chain, args.overwrite)
    else:
        block_number = args.block_number
        if isinstance(block_number, int):
            main(block_number, args.chain, args.overwrite)
        else:
            raise ValueError("not a transaction hash")
