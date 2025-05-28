import json

def load_json(filepath):
    """Utility function to load a JSON file safely."""
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)


erc20_abi = load_json("utils/erc20.abi.json")

# Get information of a transaction from the collected files
def collect_from_file(folder_prefix, filename):
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
def filter_transaction(gas_used, to_address):
    basic_transfer = 21000

    if to_address == 'empty':
        # contract creation, assuming nobody hacks here
        if gas_used > 5 * basic_transfer:
            return True

    if gas_used > 10 * basic_transfer: # Complexity detection for flash loan and reentrancy
        return True

    return False

# Sum balance changes according to trader side and public side
def separate_balance(tx_hash, folder_prefix, from_address, to_address):
    balance_change = collect_from_file(folder_prefix, '/token_info/balance.json')[tx_hash]
    address_dict = collect_from_file(folder_prefix, '/token_info/address_dict.json')
    traders = [from_address, to_address]
    trader_sum_dict = {}
    public_contract_sum_dict = {}
    for address in balance_change.keys():
        address_balance_change = balance_change.get(address)
        address_usd_change = 0
        for token in address_balance_change:
            address_usd_change += address_balance_change[token][1]
        if address == "0x0000000000000000000000000000000000000000":
            public_contract_sum_dict[address] = address_usd_change
        else:
            if address in traders:
                trader_sum_dict[address] = address_usd_change
            elif address in address_dict:
                if address_dict[address]["contractCreator"] == from_address:
                    trader_sum_dict[address] = address_usd_change
                else:
                    public_contract_sum_dict[address] = address_usd_change
            else:
                trader_sum_dict[address] = address_usd_change
    return {"trader": trader_sum_dict, "public": public_contract_sum_dict}

# Detect the balance change of given address of a transaction
def check_balance(tx_hash, folder_prefix, address, threshold):
    possible_hack = False
    balance_change = collect_from_file(folder_prefix, '/token_info/balance.json')[tx_hash]
    if address in balance_change.keys():
        address_balance_change = balance_change.get(address)
        address_usd_change = 0
        for token in address_balance_change:
            address_usd_change += address_balance_change[token][1]
        possible_hack = address_usd_change > threshold  # more strict filtered in SVM
    return possible_hack

# Detect the balance change of all addresses of a transaction
def check_balance_all(tx_hash, folder_prefix, threshold):
    balance_change = collect_from_file(folder_prefix, '/token_info/balance.json')[tx_hash]
    for address in balance_change.keys():
        address_balance_change = balance_change.get(address)
        address_usd_change = 0
        for token in address_balance_change:
            address_usd_change += address_balance_change[token][1]
        if address_usd_change > threshold:
            return True
    return False

def zero_rate_token(folder_prefix):
    zero_rate_dict = {}
    currency_dict = collect_from_file(folder_prefix, '/token_info/currency_dict.json')
    for token_address in currency_dict:
        if token_address[:2] == "0x":
            token_details = currency_dict[token_address]
            if token_details[2] == 0:
                zero_rate_dict[token_details[0]] = token_details[3]
    return zero_rate_dict

def check_total_supply(tx_hash, folder_prefix, threshold_rate):
    balance_change = collect_from_file(folder_prefix, '/token_info/balance.json')[tx_hash]
    zero_rate_dict = zero_rate_token(folder_prefix)
    if zero_rate_dict:
        for address in balance_change.keys():
            address_balance_change = balance_change.get(address)
            for token in address_balance_change:
                if token in zero_rate_dict and zero_rate_dict[token] > 1:
                    token_changed = abs(address_balance_change[token][0])
                    if zero_rate_dict[token] * threshold_rate < token_changed < zero_rate_dict[token]:
                        return True
    return False
