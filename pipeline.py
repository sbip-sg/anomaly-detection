import os
import argparse
from utils.collect_basic_info import collect_info
from utils.get_traces import collect_trace
from utils.decode_trace import decode_trace_json
from utils.token_info import collect_token
from utils.get_rpc import EndpointPool
from utils.generate_output import generate_output
from utils.collect_block import collect_block_all
from detect_utils.bytes_detection import detect_4bytes
from detect_utils.detect_all import rule_based_detection
from detect_utils.chatgpt_detect import chatgpt_detect
from detect_utils.tools import load_json
import json
import time
import pandas as pd

chain_info = load_json("utils/chain_token_dict.json")  # Token info for all chains

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
    block_tx_info_end_time  = time.time()
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
            time_dict['tx_details'][tx_hash] = {}
            tx_detail_start_time = time.time()
            # Collect traces (raw invocation tree)
            tx_folder_prefix = f"{folder_prefix}/{tx_hash}"
            os.makedirs(tx_folder_prefix, exist_ok=True)
            collect_trace(tx_hash, edpool, tx_folder_prefix)
            foundry_end_time = time.time()
            time_dict['tx_details'][tx_hash]['foundry'] = foundry_end_time - tx_detail_start_time
            # Decode trace JSON and extract information from invocation tree
            decode_trace_json(tx_folder_prefix)
            decode_end_time = time.time()
            time_dict['tx_details'][tx_hash]['decode'] = decode_end_time - foundry_end_time
            # Extract 'from' and 'to' addresses from the transaction DataFrame
            selected_tx = tx_df[tx_df['hash'] == tx_hash]
            selected_tx_dict = selected_tx.to_dict(orient="records")[0]
            if not selected_tx.empty:
                from_address = selected_tx.iloc[0]['from']
                to_address = selected_tx.iloc[0]['to']
                gas_used = selected_tx.iloc[0]['gasUsed']

                main_token, NFT_transaction = collect_token(tx_hash, chain, from_address, to_address,
                                           int(block_number), edpool, tx_folder_prefix)
                token_end_time = time.time()
                time_dict['tx_details'][tx_hash]['token'] = token_end_time - decode_end_time
                if to_address.lower() not in mev_bots:
                    detection_result, reason, la_tx = rule_based_detection(tx_hash, gas_used,
                                                    from_address, to_address, tx_folder_prefix)
                    selected_tx_dict['NFT_transaction'] = NFT_transaction
                    selected_tx_dict["detection_result"] = detection_result
                    selected_tx_dict["reason"] = reason
                    selected_tx_dict["la_tx"] = la_tx
                else:
                    selected_tx_dict['NFT_transaction'] = False
                    selected_tx_dict["detection_result"] = False
                    selected_tx_dict["reason"] = ['To address as MEV Bot']
                    selected_tx_dict["la_tx"] = False
                with open(tx_folder_prefix + f"/basic_info_{tx_hash}.json", "w") as json_file:
                    json.dump(selected_tx_dict, json_file, indent=2)
                rule_end_time = time.time()
                time_dict['tx_details'][tx_hash]['rule_based'] = rule_end_time - token_end_time
                generate_output(tx_hash, chain, selected_tx_dict, tx_folder_prefix, main_token)
                output_end_time = time.time()
                time_dict['tx_details'][tx_hash]['output'] = output_end_time - rule_end_time
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
    parser.add_argument("block_number", help="Block number for collection")
    parser.add_argument("chain", help="Ethereum block chain name")
    # use chatgpt to detect
    parser.add_argument("-llm", "--llm_detect", action="store_true", help="Use chatgpt to detect")
    # overwrite existing result
    parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite existing result")
    args = parser.parse_args()
    if "," in args.block_number:
        block_numbers = args.block_number.split(",")
        print(f'Collecting data for {len(block_numbers)} blocks.')
        for block_number in block_numbers:
            if isinstance(block_number, str) and block_number.isdigit():
                print(f'Collecting data for block {block_number}')
                main(block_number, args.chain, args.overwrite)
    else:
        block_number = args.block_number
        if isinstance(block_number, str) and block_number.isdigit():
            main(block_number, args.chain, args.overwrite)
        else:
            raise ValueError("not a transaction hash")
