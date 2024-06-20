import os
import argparse
from utils.collect_basic_info import collectinfo
from utils.get_traces import collect_trace
from utils.decode_trace import decode_trace_json
from utils.flow_tree import transform_tree
from utils.token_info import collect_token

# Choose endpoint according to transaction chain
# Plans:
#   1, Because this one can be set for only getting basic information and token symbol, we only need stable endpoints.
#   For foundry, we can choose multi-endpoints.
#   2, For rare chains, we need more testing.
RPC_ENDPOINTS = {
    "eth": [
            "https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161",
            "https://mainnet.infura.io/v3/0377f17d56934a059be55f9d96fe5134",
    ],
    "optimism": "https://op-pokt.nodies.app",
    "fantom": "https://rpc.ftm.tools",
    "arbitrum": "https://rpc.ankr.com/arbitrum",
    "bsc": "https://bscrpc.com",
    "moonriver": "https://moonriver.public.blastapi.io",
    "gnosis": "https://gnosis-rpc.publicnode.com",
    "avalanche": "https://avalanche.drpc.org",
    "polygon": "https://polygon-mainnet.public.blastapi.io",
    "celo": "https://1rpc.io/celo",
    "base": "https://developer-access-mainnet.base.org"
}

def endpoint_by_chain(chain, endpoint_idx=0):
        endpoint = RPC_ENDPOINTS[chain]
        endpoints = endpoint if type(endpoint) == list else [endpoint]
        if endpoint_idx >= len(endpoints):
                raise ValueError('No more endpoint available for this chain: ' + chain)
        return endpoints[endpoint_idx]

# Get transaction information by hash
def main(tx_hash, chain, overwrite=False, endpoint_idx=0):
        folder_prefix = f'result/{tx_hash}_{chain}'
        # Create result directory if it doesn't exist
        if overwrite:
                print(f'Deleting result folder to overwrite {tx_hash} on {chain}')
                os.system(f'rm -rf {folder_prefix}')

        os.makedirs('result', exist_ok=True)

        os.makedirs(folder_prefix, exist_ok=True)

        # Collect basic information
        # Time stamp is for getting exchange rate
        raw = (tx_hash, endpoint_by_chain(chain, endpoint_idx))
        basic_info, time_stamp_dict = collectinfo(raw)

        # Save basic information
        basic_info.to_json(folder_prefix + '/basic_info.json', orient='records', lines=True)

        # Collect traces (raw invocation flow)
        collect_trace(raw, folder_prefix)

        # Decode trace JSON and extract information from invocation flow
        decode_trace_json(folder_prefix)

        # transform invocation flow to invocation tree
        transform_tree(folder_prefix)

        # According to the decoded invocation flow, get token flow and balance changes.
        collect_token(time_stamp_dict, chain, endpoint_by_chain(chain, endpoint_idx), folder_prefix)

if __name__ == "__main__":
        parser = argparse.ArgumentParser()
        parser.add_argument("tx_hash", help="Path to the input file")
        parser.add_argument("chain", help="Transaction chain name")
        # overwrite existing result
        parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite existing result")
        args = parser.parse_args()
        main(args.tx_hash, args.chain, args.overwrite)
