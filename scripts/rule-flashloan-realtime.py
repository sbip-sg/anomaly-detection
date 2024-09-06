#  python scripts/rule-flashbot-realtime.py --web3-provider-url $ETH_RPC_ENDPOINT flashloan.realtime.txt
import csv
import argparse
from web3 import Web3
import os, sys
from datetime import datetime
import time
import requests
from itertools import chain
sys.path.insert(0, os.path.abspath(".."))
from rules import get_trancaction_by_hash, has_flashloan, has_min_gas


# parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('outfile', type=str, help='CSV file to write created contract addresses')
parser.add_argument('--web3-provider-url', type=str, help='Web3 provider url', required=True)
args = parser.parse_args()

outfile = args.outfile
WEB3_PROVIDER_URL = args.web3_provider_url

if not os.path.exists(outfile):
    print(f"Creating file {outfile}")
    output = open(args.outfile, 'a')
    outfile = csv.writer(output)
    outfile.writerow(['Block', 'Transaction Hash'])
else:
    print(f"Appending to file {outfile}")
    output = open(args.outfile, 'a')
    outfile = csv.writer(output)

w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
block_filter = w3.eth.filter('latest')


def down():
    output.flush()
    output.close()
    print("Exiting...")


def handle_block(block_hash):
    block = w3.eth.get_block(block_hash, full_transactions=True)
    for transaction in block.transactions:
        try:
            if has_flashloan(has_min_gas(transaction)):
                txhash = transaction['hash'].hex()
                row = [transaction['blockNumber'], txhash]
                outfile.writerow(row)
                output.flush()
        except KeyboardInterrupt:
            down()
            break
        except Exception as e:
            import traceback, sys
            traceback.print_exc(file=sys.stdout)
            continue

while True:
    try:
        for block_hash in block_filter.get_new_entries():
            print(f'{datetime.now()} new block: {block_hash.hex()}')
            block = w3.eth.get_block(block_hash)
            handle_block(block_hash)
    except KeyboardInterrupt:
        down()
        break
    except Exception as e:
        print(f"Exception: {e}")
        time.sleep(5)
        if '32000' in str(e):
            time.sleep(5)
            print('Restarting...')
            w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
            block_filter = w3.eth.filter('latest')
        continue
