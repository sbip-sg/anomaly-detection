import argparse
from web3 import Web3
import os, sys
sys.path.insert(0, os.path.abspath(".."))
from rules import get_trancaction_by_hash, has_flashloan, has_min_gas



# These are the transactions that are known to be hacks, taken from the tx hashs at
# https://github.com/Ztong55/attack_dataset/tree/main/eth
with open('./scripts/eth_realhacks_txs.txt', 'r') as f:
    real_hacks_txs = [line.strip() for line in f.readlines()]

parser = argparse.ArgumentParser()
parser.add_argument('--web3-provider-url', type=str, help='Web3 provider url', required=True)
args = parser.parse_args()

WEB3_PROVIDER_URL = args.web3_provider_url


w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
block_filter = w3.eth.filter('latest')

def handle_transactions(transactions):
    detected = []
    failed = []
    for (txhash, transaction) in transactions:
        try:
            if has_flashloan(has_min_gas(transaction)):
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
transactions = [(txhash, get_trancaction_by_hash(w3, txhash)) for txhash in real_hacks_txs]

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
