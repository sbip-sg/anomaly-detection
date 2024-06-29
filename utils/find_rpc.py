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
    "polygon": "https://rpc.ankr.com/polygon",
    "celo": "https://1rpc.io/celo",
    "base": "https://developer-access-mainnet.base.org"
}

endpoint_idx = 0

def endpoint_by_chain(chain):
    global endpoint_idx
    if chain in RPC_ENDPOINTS.keys():
        endpoint = RPC_ENDPOINTS[chain]
    else:
        raise ValueError('No endpoint available for this chain: ' + chain)
    endpoints = endpoint if type(endpoint) == list else [endpoint]
    if endpoint_idx >= len(endpoints):
        raise ValueError('No more endpoint available for this chain: ' + chain)
    return endpoints[endpoint_idx]

def handle_error(chain):
    global endpoint_idx
    endpoint = RPC_ENDPOINTS[chain]
    if endpoint_idx +1 < len(endpoint):
        endpoint_idx += 1
        return True
    else:
        raise ValueError('No more endpoint available for this chain: ' + chain)