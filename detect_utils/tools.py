import json

def load_json(filepath):
    """Utility function to load a JSON file safely."""
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)

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

# Detect the balance change of given address of a transaction
def check_balance(tx_hash, folder_prefix, address):
    possible_hack = False
    balance_change = collect_from_file(folder_prefix, '/token_info/balance.json')[tx_hash]
    if address in balance_change.keys():
        address_balance_change = balance_change.get(address)
        address_usd_change = 0
        for token in address_balance_change:
            address_usd_change += address_balance_change[token][1]
        possible_hack = address_usd_change > 27000  # more strict filtered in SVM
    return possible_hack

# Detect the balance change of all addresses of a transaction
def check_balance_all(tx_hash, folder_prefix, threshold):
    balance_change = collect_from_file(folder_prefix, '/token_info/balance.json')[tx_hash]
    for address in balance_change.keys():
        address_balance_change = balance_change.get(address)
        address_usd_change = 0
        for token in address_balance_change:
            address_usd_change += address_balance_change[token][1]
        suspicious = abs(address_usd_change) > threshold
        if suspicious:
            return suspicious