import argparse
from web3 import Web3
import os
import json
from datetime import datetime
import time
import requests
from itertools import chain

# These are the transactions that are known to be hacks, taken from the tx hashs at
# https://github.com/Ztong55/attack_dataset/tree/main/eth
with open('eth_realhacks_txs.txt', 'r') as f:
    real_hacks_txs = [line.strip() for line in f.readlines()]

# proxies = {
#     'http': 'socks5h://localhost:9050',
#     'https': 'socks5h://localhost:9050'
# }

proxies = None


MIN_CALL_LENGTH = 6 # the low the more false positives
assert MIN_CALL_LENGTH > 1

api_trace_uri  = '/api/v1/onchain/tx/trace'
api_balance_change = '/api/v1/onchain/tx/balance-change'
api_address_label = '/v1/onchain/tx/address-label'
api_state_change = '/api/v1/onchain/tx/state-change'
api_profile = '/api/v1/onchain/tx/profile'

seen = set()

parser = argparse.ArgumentParser()
parser.add_argument('--web3-provider-url', type=str, help='Web3 provider url', required=True)
args = parser.parse_args()

WEB3_PROVIDER_URL = args.web3_provider_url


w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
block_filter = w3.eth.filter('latest')




def filter_transaction(transaction):
    # txhash = transaction['hash'].hex()
    gas_used = transaction.get('gas')
    # gas_price = transaction.get('gasPrice')
    # max_priority_fee = transaction.get('maxPriorityFeePerGas', 0)
    # base_fee = block.baseFeePerGas
    base_gas = 21000

    if gas_used > base_gas * 10: # high tips
        return transaction

    if transaction.get('to') is None:
        # contract creation, assuming nobody hacks here
        if gas_used > base_gas * 50: # TODO update this threshold if necessary
            return transaction

    if gas_used > base_gas * 100: # TODO update this threshold if necessary
        return transaction

    return None

def fetch_phalcon_data(txhash, uri, chain_id=1, data=None, timeout=10):
    url = f'https://app.blocksec.com{uri}'

    headers = {
        'accept': 'application/json',
        'accept-language': 'en;q=0.9',
        'content-type': 'application/json;charset=utf-8',
        'origin': 'https://app.blocksec.com',
        'referer': 'https://app.blocksec.com',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Brave";v="126"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }

    data = data or {
        "chainID": chain_id,
        "txnHash": txhash,
        "blocked": False
    }

    response = requests.post(url, headers=headers, json=data, timeout=timeout, proxies=proxies)
    response.raise_for_status()
    return response.json()


def has_cycle(xs):
    n = len(xs)
    for seq_len in range(2, n // 2 + 1):
        for i in range(n - seq_len + 1):
            subsequence = tuple(xs[i:i + seq_len])
            remaining_calls = xs[i + seq_len:]

            if len(subsequence) >= MIN_CALL_LENGTH and subsequence in zip(*[remaining_calls[j:] for j in range(seq_len)]):
                return subsequence

    return None

# Detector containing two checks to be considered as possible hack:
# 1. cyclic calls in transactions: each sequence of calls with minimum length MIN_CALL_LENGTH
# 2. if the sender's balance changes by more than 10k USD
def detect_transaction(transaction):
    if transaction is None:
        return None
    txhash = transaction['hash'].hex()
    sender = transaction['from'].lower()

    trace = fetch_phalcon_data(txhash, api_trace_uri)

    data_map = trace['dataMap']
    ids = [int(id) for id in data_map.keys()]
    ids = sorted(ids)
    functions = []



    for id in ids:
        t = trace['dataMap'][str(id)]
        if 'event' in t:
            pass # ignore event in this detector
        elif 'invocation' in t:
            f = t['invocation']
            functions.append((f['fromAddress'], f['address'] , f['selector']))
        else:
            print(f"Unknown trace type: {t}")

    possible_hack = False
    if has_cycle(functions) is not None:
        balance_change = fetch_phalcon_data(txhash, api_balance_change)

        sender_balance_change = [c['assets'] for c in balance_change['balanceChanges'] if c['account'] == sender]
        sender_balance_change = list(chain.from_iterable(sender_balance_change)) # flatten
        sender_usd_change = sum([(1 if c['sign'] else -1) * float(c['value'].replace(',','') or 0) for c in sender_balance_change]) # ignores asset with unknown values
        possible_hack = sender_usd_change > 10000 # 10k USD


    if possible_hack:
        print(f'Detected: {txhash}')

    return  possible_hack

def handle_transactions(transactions):
    detected = []
    failed = []
    for (txhash, transaction) in transactions:
        try:
            if detect_transaction(filter_transaction(transaction)):
                detected.append(txhash)
        except KeyboardInterrupt:
            break
        except Exception as e:
            import traceback, sys
            traceback.print_exc(file=sys.stdout)
            failed.append(txhash)
            continue
    return (detected, failed)


print('Loading transactions ...')
transactions = [(txhash, w3.eth.get_transaction(txhash)) for txhash in real_hacks_txs]

print('Processing transactions ...')
detected, failed = handle_transactions(transactions)

print(f'Total realhack transactions: {len(transactions)}')
print(f'Detected transactions: {len(detected)}' )
print(f'Failed to process: {len(failed)}' )

with open('realhacks_detected.txt', 'w') as f:
    for txhash in list(detected):
        f.write(txhash + "\n")


with open('realhacks_failed_to_process.txt', 'w') as f:
    for txhash in list(failed):
        f.write(txhash + "\n")
