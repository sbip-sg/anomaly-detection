import json
from os import listdir
from eth_abi import decode
from utils.get_rate import get_rate

# Base URL for Etherface API
base_url = "https://api.etherface.io/v1/signatures/hash/all/"

# Function to decode input data based on event text and input hash
def decode_input(event_text, input_hash):
    input_list = []
    if len(input_hash) % 64 == 0:
        if len(event_text.split('(', 1)) != 1 and len(input_hash) != 0 and len(event_text.split(';')) == 1:
            start_index = event_text.find('(')
            end_index = event_text.rfind(')')
            raw_parameters = event_text[start_index + 1:end_index]
            if len(raw_parameters) != 0:
                parameters = split_parameters(raw_parameters)
                values = decode(parameters, bytes.fromhex(input_hash))
                for value in values:
                    input_list.append(value)
        elif len(input_hash) != 0:
            chunks = [input_hash[i:i + 64] for i in range(0, len(input_hash), 64)]
            for line in chunks:
                count_of_zeros = len(line) - len(line.lstrip('0'))
                if count_of_zeros >= 24 and count_of_zeros < 30:
                    input_list.append(decode(['address'], bytes.fromhex(line))[0])
                elif count_of_zeros >= 30 and count_of_zeros < 60:
                    input_list.append(decode(['uint256'], bytes.fromhex(line))[0])
    start_index = event_text.find('(')
    end_index = event_text.rfind(')')
    raw_parameters = event_text[start_index + 1:end_index]
    if len(raw_parameters) != 0 and len(input_list) == 0:
        chunks = [input_hash[i:i + 64] for i in range(0, len(input_hash), 64)]
        for line in chunks:
            count_of_zeros = len(line) - len(line.lstrip('0'))
            if count_of_zeros >= 24 and count_of_zeros < 30:
                input_list.append(decode(['address'], bytes.fromhex(line))[0])
            elif count_of_zeros >= 30 and count_of_zeros < 60:
                input_list.append(decode(['uint256'], bytes.fromhex(line))[0])
    return input_list

# Function to check if parentheses are balanced in a string
def are_parentheses_balanced(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}

    for char in s:
        if char in mapping.values():
            stack.append(char)
        elif char in mapping:
            if not stack or stack.pop() != mapping[char]:
                return False

    return not stack

# Function to split parameters in a string
def split_parameters(s):
    s_list = s.split(',')
    i = 0
    while i != len(s_list) - 1:
        if are_parentheses_balanced(s_list[i]):
            i += 1
        else:
            # Merge s_list[i] and s_list[i+1]
            s_list[i] += ',' + s_list[i + 1]
            s_list.pop(i + 1)

    return s_list

# Function to update summary dictionary with transaction details
def update_summary(summary, address, currency, amount):
    if address not in summary:
        summary[address] = {}
    if currency not in summary[address]:
        summary[address][currency] = 0

    summary[address][currency] += amount/1e18
    return summary

# Function to deal with ETH transfer transactions
def deal_ethtransfer(summary, trace, flow):
    from_address = trace["action"]["from"]
    to_address = trace["action"]["to"]
    amount = int(trace["action"]["value"][2:], 16)

    summary = update_summary(summary, from_address, 'ETH', -amount)
    summary = update_summary(summary, to_address, 'ETH', amount)
    flow.loc[len(flow)] = [from_address, to_address, 'ETH', amount/1e18]

    return summary

# Function to deal with contract creation transactions
def deal_create(summary, trace, flow):
    from_address = trace["action"]["from"]
    amount = int(trace["action"]["value"][2:], 16)
    to_address = trace["result"]["address"]

    summary = update_summary(summary, from_address, 'ETH', -amount)
    summary = update_summary(summary, to_address, 'ETH', amount)
    flow.loc[len(flow)] = [from_address, to_address, 'ETH', amount/1e18]

    return summary

# Function to deal with selfdestruct transactions
def deal_selfdestruct(summary, trace, flow):
    from_address = trace["action"]["address"]
    amount = int(trace["action"]["balance"][2:], 16)
    to_address = trace["action"]["refundAddress"]

    summary = update_summary(summary, from_address, 'ETH', -amount)
    summary = update_summary(summary, to_address, 'ETH', amount)
    flow.loc[len(flow)] = [from_address, to_address, 'ETH', amount/1e18]

    return summary

# Function to collect ETH transaction details
def collect_eth(total_dict, timestamp_dict, flow, folder_prefix="result"):
    # Get list of JSON files in trace_json directory
    jsonlist = listdir(folder_prefix + '/trace_json')

    dict1 = total_dict
    for i in jsonlist:
        summary_dict = {}
        file = open(folder_prefix + '/trace_json/' + i)
        tx = json.load(file)
        if tx[0]["transactionHash"] in dict1.keys():
            new_dict = dict1[tx[0]["transactionHash"]]
        else:
            dict1[tx[0]["transactionHash"]] = {}
            new_dict = dict1[tx[0]["transactionHash"]]
        for trace in tx:
            if 'error' not in trace.keys():
                if trace['type'] == 'call' and trace["action"]["callType"] != "delegatecall" and int(
                        trace["action"]["value"][2:], 16) != 0:
                    summary_dict = deal_ethtransfer(summary_dict, trace, flow)
                elif trace['type'] == 'create' and int(trace["action"]["value"][2:], 16) != 0:
                    summary_dict = deal_create(summary_dict, trace, flow)
                elif trace['type'] == 'suicide' and int(trace["action"]["balance"][2:], 16) != 0:
                    summary_dict = deal_selfdestruct(summary_dict, trace, flow)
        time_stamp = timestamp_dict[tx[0]["transactionHash"]]
        rate = get_rate(time_stamp, 'ETH')
        for user in summary_dict.keys():
            if summary_dict[user]['ETH'] != 0:
                if user not in new_dict.keys():
                    new_dict[user] = {}
                new_dict[user]['ETH'] = [summary_dict[user]['ETH'],summary_dict[user]['ETH']*rate]
    for key1 in dict1.keys():
        for key2 in dict1[key1].keys():
            keys_to_delete = [key for key, value in dict1[key1][key2].items() if value == 0]
            for key3 in keys_to_delete:
                del dict1[key1][key2][key3]
    for key1 in dict1.keys():
        keys_to_delete = [key for key, value in dict1[key1].items() if value == {}]
        for key2 in keys_to_delete:
            del dict1[key1][key2]
    with open(folder_prefix + '/balance.json', 'w') as json_file:
        json.dump(dict1, json_file, indent=2)

    flow.to_json(folder_prefix + '/tokenflow.json', orient='records', lines=True)
