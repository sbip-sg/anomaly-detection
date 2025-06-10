import json
from collections import defaultdict

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
def separate_balance(tx_hash, tx_timestamp, folder_prefix, from_address, to_address):
    balance_change = collect_from_file(folder_prefix, '/token_info/balance.json')[tx_hash]
    address_dict = collect_from_file(folder_prefix, '/token_info/address_dict.json')
    if to_address not in address_dict:
        senders = [from_address, to_address]
    else:
        to_info = address_dict[to_address]
        if (not to_info['contractFactory']) and int(tx_timestamp) - int(to_info["timestamp"]) < 86400:
            senders = [from_address, to_address]
        else:
            senders = [from_address]
    sender_sum_dict = {}
    public_sum_dict = {}
    trader_sum_dict = {}
    for address in balance_change.keys():
        address_balance_change = balance_change.get(address)
        if address == "0x0000000000000000000000000000000000000000":
            public_sum_dict[address] = address_balance_change
        else:
            if address in senders:
                sender_sum_dict[address] = address_balance_change
            elif address in address_dict:
                if address_dict[address]["contractCreator"] == from_address:
                    sender_sum_dict[address] = address_balance_change
                else:
                    public_sum_dict[address] = address_balance_change
            else:
                trader_sum_dict[address] = address_balance_change
    return {"sender": sender_sum_dict, "trader": trader_sum_dict, "public": public_sum_dict}

def sum_group(group_data):
    summed = defaultdict(lambda: [0, 0])
    usd_sum = 0
    for address, tokens in group_data.items():
        for token, (amount, usd) in tokens.items():
            summed[token][0] += amount
            summed[token][1] += usd
            usd_sum += usd
    return dict(summed), usd_sum

def abs_sum_group(group_data):
    abs_sum = defaultdict(lambda: [0, 0])
    abs_usd_sum = 0
    for address, tokens in group_data.items():
        for token, (amount, usd) in tokens.items():
            abs_sum[token][0] += abs(amount)
            abs_sum[token][1] += abs(usd)
            abs_usd_sum += abs(usd)
    return dict(abs_sum), abs_usd_sum

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
def check_balance_all(tx_hash, checking_list, folder_prefix, threshold):
    balance_change = collect_from_file(folder_prefix, '/token_info/balance.json')[tx_hash]
    if not checking_list:
        checking_list = list(balance_change.keys())
    for address in checking_list:
        if address in balance_change:
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

def self_created(selected_tx_dict):
    if selected_tx_dict['to'] == "empty":
        return True
    elif (selected_tx_dict['to_creator'] ==  selected_tx_dict['from'] and int(selected_tx_dict["timestamp"])
          - int(selected_tx_dict["to_timestamp"]) < 2600000):
        return True
    return False

def flow_in(separated_balance, is_nft):
    abnormal_flow = False
    token_thief = False
    senders, senders_sum = sum_group(separated_balance['sender'])
    traders, traders_sum = sum_group(separated_balance['trader'])
    contracts, contracts_sum = sum_group(separated_balance['public'])
    _, sender_abs_sum = abs_sum_group(separated_balance['sender'])
    _, trader_abs_sum = abs_sum_group(separated_balance['trader'])
    _, contract_abs_sum = abs_sum_group(separated_balance['public'])
    max_abs_sum = max([sender_abs_sum, trader_abs_sum, contract_abs_sum])
    if max_abs_sum > 27000:
        factor = 0.05
    else:
        factor = 0.1
    flow_in_type = None
    if senders_sum > 10 and senders_sum > max_abs_sum * factor * 0.1:
        if senders_sum > max_abs_sum * factor or senders_sum > 63000:
            abnormal_flow, token_thief = True, False
            if traders_sum < contracts_sum:
                flow_in_type = "sender large profit from other EOA"
            else:
                flow_in_type = "sender large profit from contracts"
    elif traders_sum == trader_abs_sum and contracts_sum < senders_sum and traders_sum > 1000:
        abnormal_flow, token_thief = True, False
        flow_in_type = "other EOA from contracts"
    elif max_abs_sum <= 10 and not len(contracts):
        if len(senders) == 1:
            token, data = next(iter(senders.items()))
            if data[0] > 0:
                abnormal_flow, token_thief = True, True
                flow_in_type = "senders steal token from EOA"
    if is_nft and not abnormal_flow:
        count = 0
        abs_count = 0
        trader_count = 0
        for token in senders:
            if '_' in token:
                count += senders[token][0]
                abs_count += 1
                if token in traders:
                    trader_count += traders[token][0]
        if count == abs_count and trader_count + count == 0:
            abnormal_flow, token_thief = True, True
            flow_in_type = "senders steal nfts from EOA"
    return abnormal_flow, token_thief, flow_in_type