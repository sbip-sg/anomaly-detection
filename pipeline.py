import os
import argparse
from utils.collect_basic_info import collect_info
from utils.get_traces import collect_trace
from utils.decode_trace import decode_trace_json
from utils.token_info import collect_token
from utils.get_rpc import EndpointPool
from detect_utils.rule_cyclic_calls import detect_cyclic_transaction
from detect_utils.rule_flashloan import detect_flashloan_transaction
import json


# Get transaction information by hash
def main(tx_hash, chain, overwrite=False):
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
    basic_info, time_stamp = collect_info(tx_hash, edpool)

    with open(folder_prefix + '/basic_info.json', 'w') as jsonfile:
        json.dump(basic_info, jsonfile, indent=2)

    # Collect traces (raw invocation tree)
    collect_trace(tx_hash, edpool, folder_prefix)

    # Decode trace JSON and extract information from invocation tree
    decode_trace_json(folder_prefix)

    # According to the decoded invocation tree, get token flow and balance changes.
    collect_token(time_stamp, edpool, folder_prefix)

    detection_result = False


    if detect_cyclic_transaction(tx_hash, chain):
        print('Suspicious Reentrancy Attack Detected')  # To be updated
        detection_result = True

    if detect_flashloan_transaction(tx_hash, chain):
        print('Suspicious Flashloan Attack Detected')  # To be updated
        detection_result = True

    basic_info['detection_result'] = detection_result

    # Save basic information
    with open(folder_prefix + '/basic_info.json', 'w') as jsonfile:
        json.dump(basic_info, jsonfile, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tx_hash", help="Path to the input file")
    parser.add_argument("chain", help="Transaction chain name")
    # overwrite existing result
    parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite existing result")
    args = parser.parse_args()
    main(args.tx_hash, args.chain, args.overwrite)
