import os
import argparse
from utils.collect_basic_info import collect_info
from utils.get_traces import collect_trace
from utils.decode_trace import decode_trace_json
from utils.token_info import collect_token
from utils.get_rpc import EndpointPool
from utils.db_tools import save_new_line
from detect_utils.detect_all import rule_based_detection


# Get transaction information by hash
def main(tx_hash, chain, overwrite=False):
    folder_prefix = 'result'
    os.makedirs(folder_prefix, exist_ok=True)

    edpool = EndpointPool(chain)
    # Collect basic information
    # Time stamp is for getting exchange rate
    basic_info = collect_info(tx_hash, edpool)
    basic_info['chain'] = chain

    save_new_line(basic_info, folder_prefix + '/basic_info.csv', ['transaction_hash'])

    new_hash = tx_hash + '_' + chain
    # Collect traces (raw invocation tree)
    formal_result = collect_trace(new_hash, edpool, folder_prefix)

    # Decode trace JSON and extract information from invocation tree
    decode_trace_json(new_hash, formal_result, folder_prefix)

    # According to the decoded invocation tree, get token flow and balance changes.
    # collect_token(tx_hash, basic_info['blocknumber'], edpool, folder_prefix)

    # detection_result, reason = rule_based_detection(tx_hash, chain)

    # basic_info['detection_result'] = detection_result
    # basic_info['reason'] = reason

    # Save basic information
    # with open(folder_prefix + '/basic_info.json', 'w') as json_file:
    #     json.dump(basic_info, json_file, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tx_hash", help="Path to the input file")
    parser.add_argument("chain", help="Transaction chain name")
    # overwrite existing result
    parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite existing result")
    args = parser.parse_args()
    main(args.tx_hash, args.chain, args.overwrite)
