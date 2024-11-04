# Choose endpoint according to transaction chain
# Plans:
#   1, Because this one can be set for only getting basic information and token symbol, we only need stable endpoints.
#   For foundry, we can choose multi-endpoints.
#   2, For rare chains, we need more testing.
import time
import random


class EndpointPool:
    cooldown_time_secs = 60
    # a dict from chain -> a set of endpoints
    usable_endpoints = {
        "eth": [
                "http://sbip-g3.d2.comp.nus.edu.sg:8545",
                "https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161",
                "https://mainnet.infura.io/v3/0377f17d56934a059be55f9d96fe5134"
                ],
        "optimism": ["https://op-pokt.nodies.app"],
        "fantom": ["https://rpc.ftm.tools"],
        "arbitrum": ["https://rpc.ankr.com/arbitrum"],
        "bsc": ["https://bscrpc.com"],
        "moonriver": ["https://moonriver.public.blastapi.io"],
        "gnosis": ["https://gnosis-rpc.publicnode.com"],
        "avalanche": ["https://avalanche.drpc.org"],
        "polygon": ["https://rpc.ankr.com/polygon"],
        "celo": ["https://1rpc.io/celo"],
        "base": ["https://developer-access-mainnet.base.org"]
    }

    broken_endpoints = {}

    def __init__(self, chain):
        self.chain = chain
        self.endpoints = self.usable_endpoints.get(chain, {})
        self.broken_endpoints[chain] = {}

    def mark_endpoint_broken(self, endpoint):
        '''Mark the endpoint as broken at the current timestamp.'''
        self.endpoints.remove(endpoint)
        now = time.time()
        if endpoint not in self.broken_endpoints[self.chain]:
            self.broken_endpoints[self.chain][endpoint] = now
        else:
            del self.broken_endpoints[self.chain][endpoint]

        return self.endpoint_by_chain()

    def reload_endpoint(self):
        '''Put the broken endpoints back to the usable endpoint, if the cooldown time has passed'''
        now = time.time()

        if not self.broken_endpoints[self.chain]:
            raise ValueError('no more usable endpoint available for this chain: ' + self.chain)

        for endpoint in self.broken_endpoints[self.chain]:
            if now - self.broken_endpoints[self.chain][endpoint] > self.cooldown_time_secs:
                self.endpoints.append(endpoint)

    def endpoint_by_chain(self):

        '''Get first available endpoint to use, or raise `FindEndpointException` if no more usable endpoint available'''
        if not self.endpoints:
            self.reload_endpoint()
            if not self.endpoints:
                raise ValueError('no more endpoint available for this chain: ' + self.chain)

        return random.choice(self.endpoints)
