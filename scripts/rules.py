import requests
import hashlib
from pathlib import Path
import os
import json
from web3 import Web3

SOCKS5_PORT = os.environ.get('USE_SOCKS5_PORT')


def md5(string):
    md5_hash = hashlib.md5(string.encode())
    return md5_hash.hexdigest()


def get_from_cache(key: str):
    cache_file = os.path.join(Path.home(), '.anomaly-detection-cache', key)
    if not os.path.exists(cache_file):
        return None

    with open(cache_file, 'r') as f:
        return f.read()

def write_cache(key: str, data: str):
    cache_file = os.path.join(Path.home(), '.anomaly-detection-cache', key)
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, 'w') as f:
        f.write(data)

def wrap_cache(keyfn=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_key = md5(f'{args}-{kwargs}') if keyfn is None else keyfn(*args, **kwargs)
            cached_data = get_from_cache(cache_key)
            if cached_data:
                return json.loads(cached_data)
            data = func(*args, **kwargs)
            try:
                write_cache(cache_key, json.dumps(data))
            except Exception as e:
                write_cache(cache_key, Web3.to_json(data))
            return data
        return wrapper
    return decorator

api_trace_uri  = '/api/v1/onchain/tx/trace'
api_balance_change = '/api/v1/onchain/tx/balance-change'
api_address_label = '/v1/onchain/tx/address-label'
api_state_change = '/api/v1/onchain/tx/state-change'
api_profile = '/api/v1/onchain/tx/profile'

if SOCKS5_PORT:
    proxies = {
        'http': f'socks5h://localhost:{SOCKS5_PORT}',
        'https': f'socks5h://localhost:{SOCKS5_PORT}'
    }
else:
    proxies = {}


@wrap_cache()
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

def has_cyclic_calls(transaction):
    pass


def has_flashloan(transaction):
    if transaction is None:
        return
    txhash = transaction['hash']
    if type(txhash) != str:
        txhash = txhash.hex()

    trace = fetch_phalcon_data(txhash, api_trace_uri)

    data_map = trace['dataMap']
    ids = [int(id) for id in data_map.keys()]
    ids = sorted(ids)
    address_list = []
    for id in ids:
        t = trace['dataMap'][str(id)]
        if 'event' in t:
            pass # ignore event in this detector
        elif 'invocation' in t:
            f = t['invocation']
            function_name = (f.get('decodedMethod') or {}).get('name', '')
            if function_name.lower() == 'flashLoan':
                params = (f.get('decodedMethod') or {}).get('callParams', '')
                for parameter in params:
                    if ('recipient' in (parameter or {}).get('name', '').lower()
                            or 'receiver' in (parameter or {}).get('name', '')
                            or 'to' in (parameter or {}).get('name', '').lower()):
                        if  (parameter or {}).get('value', '') not in address_list:
                            # Assume param['value'] can be a single value or a list
                            value = (parameter or {}).get('value', '')

                            # Check if the value is a list
                            if isinstance(value, list):
                                # Append the first element of the list
                                address_list.append(value[0])
                            else:
                                # Append the value directly if it's not a list
                                address_list.append(value)

            if function_name.lower() == 'flashloan':
                print(f'Flashloan detected in {txhash}')
                return transaction
        else:
            print(f"Unknown trace type: {t}")

    if len(address_list) != 0:
        balance_change = fetch_phalcon_data(txhash, api_balance_change)
        balance = (balance_change or {}).get('balanceChanges', '')
        possiblelist = []
        for accountdict in balance:
            if (accountdict or {}).get('account', '') in address_list:
                assets = (address_list or {}).get('assets', '')
                possible = False
                signs = []
                for asset in assets:
                    # sign means income(True) and outcome(False)
                    sign = (asset or {}).get('sign', '')
                    if sign not in signs:
                        signs.append(sign)
                if len(signs) == 1:
                    possible = signs[0]
                    # Possiblelist is the possibilities of all receiver accounts
                possiblelist.append(possible)
        possibility = 0
        if len(possiblelist) != 0:
            possibility = sum(possiblelist) / len(possiblelist)
        if possibility > 0.5:
            print(f'Flashloan detected in {txhash}')
            return True
        else:
            return False

    return False

def has_min_gas(transaction):
    assert transaction is not None
    assert type(transaction) != str
    gas_used = transaction.get('gas')
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

@wrap_cache(keyfn=lambda _, x: x)
def get_trancaction_by_hash(web3, txhash):
    return web3.eth.get_transaction(txhash)
