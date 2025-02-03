import os
import argparse
from utils.collect_basic_info import collect_info
from utils.get_traces import collect_trace
from utils.decode_trace import decode_trace_json
from utils.token_info import collect_token
from utils.get_rpc import EndpointPool
from utils.generate_output import generate_output
from detect_utils.detect_all import rule_based_detection
from detect_utils.chatgpt_detect import chatgpt_detect
from detect_utils.deepseekv3_detect import deepseekv3_detect
import json


# Get transaction information by hash
def main(tx_hash, chain, overwrite=False, use_llm=False):
    folder_prefix = f'result/{tx_hash}_{chain}'
    # Create result directory if it doesn't exist
    if overwrite:
        print(f'Deleting result folder to overwrite {tx_hash} on {chain}')
        os.system(f'rm -rf {folder_prefix}')

    os.makedirs('result', exist_ok=True)

    os.makedirs(folder_prefix, exist_ok=True)

    edpool = EndpointPool(chain)
    # Collect basic information
    # Time stamp is for getting exchange rate
    basic_info = collect_info(tx_hash, edpool)

    with open(folder_prefix + '/basic_info.json', 'w') as json_file:
        json.dump(basic_info, json_file, indent=2)

    # Collect traces (raw invocation tree)
    collect_trace(tx_hash, edpool, folder_prefix)

    # Decode trace JSON and extract information from invocation tree
    decode_trace_json(folder_prefix)

    # According to the decoded invocation tree, get token flow and balance changes.
    collect_token(tx_hash, basic_info['from'], basic_info['to'], basic_info['blocknumber'], edpool, folder_prefix)

    detection_result, reason = rule_based_detection(tx_hash, chain)

    basic_info['detection_result'] = detection_result
    basic_info['reason'] = reason

    # Save basic information
    with open(folder_prefix + '/basic_info.json', 'w') as json_file:
        json.dump(basic_info, json_file, indent=2)

    generate_output(tx_hash, chain, folder_prefix)

    # if use_chatgpt and detection_result:
    if use_llm:
        try:
            # chatgpt_detect(tx_hash, folder_prefix)
            deepseekv3_detect(tx_hash, folder_prefix)
        except Exception as e:
            print('Chatgpt Error:', e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tx_hash", help="Path to the input file")
    parser.add_argument("chain", help="Transaction chain name")
    # use chatgpt to detect
    parser.add_argument("-llm", "--llm_detect", action="store_true", help="Use chatgpt to detect")
    # overwrite existing result
    parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite existing result")
    args = parser.parse_args()
    main(args.tx_hash, args.chain, args.overwrite, args.llm_detect)
