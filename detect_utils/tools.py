import json

# Get information of a transaction from the collected files
def collect_from_file(tx_hash, chain, filename):
    folder_prefix = f'result/{tx_hash}_{chain}'
    with open(folder_prefix + filename) as input_json:
        output_json = json.load(input_json)
    return output_json

def unknown_first_call(trace):
    for element in trace:
        if 'create' in element['type'] and len(element['location']) <= 1:
            return True
        if element['type'] == 'call':
            if element['functionName'] == element['selector'] and len(element['location']) <= 3:
                return True
            else:
                return False

# Filter transactions by their gas usage.
def filter_transaction(basic_info, trace):
    gas_used = basic_info.get('gasUsed')
    to_address = basic_info.get('to')
    base_gas = 21000

    if to_address == 'empty' or unknown_first_call(trace):
        # contract creation, assuming nobody hacks here
        if gas_used > base_gas * 5:  # TODO update this threshold if necessary
            return True

    if gas_used > base_gas * 10:  # TODO update this threshold if necessary
        return True

    return False

# Detect the balance change of given address of a transaction
def check_balance(tx_hash, chain, address):
    possible_hack = False
    balance_change = collect_from_file(tx_hash, chain, '/token_info/balance.json')[tx_hash]
    if address in balance_change.keys():
        address_balance_change = balance_change.get(address)
        address_usd_change = 0
        for token in address_balance_change:
            address_usd_change += address_balance_change[token][1]
        possible_hack = address_usd_change > 10000  # 10k USD
    return possible_hack
