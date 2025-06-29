import os
from web3 import Web3
import requests
from utils.collect_basic_info import collect_info
from utils.get_traces import collect_trace
from utils.decode_trace import decode_trace_json
from utils.token_info import collect_token
from utils.generate_output import generate_output

def get_transactions(address, block_number, page=1, offset=40, sort='asc'):
    url = "https://api.etherscan.io/v2/api"
    address = Web3.to_checksum_address(address)
    params = {
        'chainid': 1,
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'startblock': block_number - 1000,
        'endblock': block_number - 1,
        'page': page,
        'offset': offset,
        'sort': sort,
        'apikey': "VVAXBFG3KQAZHF4EGQ2FTTFES5ZA1WS3UZ"
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data.get('status') == '1':
            return data.get('result')
        else:
            return []
    else:
        print(f"HTTP Error {response.status_code}: {response.text}")
        return []

def transaction_search(address, block_number, identifier):
    transactions = get_transactions(address, block_number)
    few_shot_list = []
    for tx in transactions:
        if tx['input'][:10] == identifier:
            few_shot_list.append(tx)
    return few_shot_list[:2]

def few_shot_output(address, block_number, identifier, edpool, folder_prefix, chain):
    few_shot_list = transaction_search(address, block_number, identifier)
    if few_shot_list:
        few_shot_folder = f"{folder_prefix}/few_shots"
        os.makedirs(few_shot_folder, exist_ok=True)
        for tx in few_shot_list:
            tx_hash = tx['hash']
            tx_folder_prefix = f"{few_shot_folder}/{tx_hash}"
            os.makedirs(tx_folder_prefix, exist_ok=True)
            basic_info = collect_info(tx_hash, edpool)
            collect_trace(tx_hash, edpool, tx_folder_prefix)
            decode_trace_json(tx_folder_prefix)
            main_token, _ = collect_token(tx_hash, chain, tx['from'], tx['to'],
                                                        int(tx['blockNumber']), edpool, tx_folder_prefix)
            generate_output(tx_hash, chain, basic_info, tx_folder_prefix, main_token)
        return True
    return False



