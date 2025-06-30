from utils.tools import collect_from_file
import tiktoken
from collections import defaultdict, Counter
import re

# whether a string is a hex with len 64
def is_hex64(s):
    return bool(re.fullmatch(r'[0-9a-f]{64}', s))

# use tiktoken package to estimate token amount
def count_tokens(text, model="o1-"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

# count function name
def count_names(dict_list, name):
    return dict(Counter(d[name].split("(")[0] for d in dict_list if name in d))

def add_to_key_list_dict(d, key, item):
    """
    Adds `item` to the list under `key` in dictionary `d`.
    If `key` does not exist, creates a new list for it.

    Parameters:
        d (dict): A dictionary with lists as values.
        key: The key to add the item under.
        item: The item to add to the key's list.
    """
    if key not in d:
        d[key] = []
    d[key].append(item)

# make addresses of dict to shortened address list
def address_dict_to_key_list(input_dict):
    key_list = []
    for address in input_dict:
        if shorten_address(address) != "0x00000000":
            key_list.append(shorten_address(address))
    return key_list

def rounded_number(number, usd_mode=False):
    """
    Rounds the number based on the selected mode.

    Usd Mode: Always rounds to two decimal places.
    Other Value Mode:
        - If number >= 1, rounds to two decimal places.
        - If number < 1, rounds to two significant figures.

    :param number: The number to round (float or int)
    :param usd_mode: Boolean flag to determine USD rounding mode.
    :return: The rounded number
    """
    try:
        if not isinstance(number, (int, float)):
            print(f"Not a number: {number}")
            return 0

        if usd_mode:
            return round(number)
        else:
            if abs(number) >= 1:
                return round(number, 2)
            elif number == 0:
                return 0.0
            else:
                from math import log10, floor
                significant_figures = 2
                order = floor(log10(abs(number)))
                return round(number, -order + (significant_figures - 1))
    except ValueError as e:
        print(e)
        return None


# Shorten address length to 10 (4bytes)
def shorten_address(address):
    if isinstance(address, str):
        if address.startswith('0x') and len(address) == 42:
            result = address[:10]
            if result == "0x00000000":
                result = f"0x{address[-8:]}"
            return result
        else:
            return address
    else:
        raise TypeError('Non-string as address')

# sum the balance change of group of addresses
def sum_address_group(group_data):
    summed = defaultdict(lambda: [0, 0])
    usd_sum = 0
    for address in group_data:
        token_dict = group_data[address]
        for token, (amount, usd) in token_dict.items():
            if "_" in token and token.split("_")[1][:2] != "0x":
                token = "nft " + token.split("_")[0]
            summed[token][0] += amount
            summed[token][1] += usd
            usd_sum += usd
    return dict(summed), usd_sum

# use address information dict to judge an address
def judge_address(address, address_dict, from_add, to_add):
    if address == "0x0000000000000000000000000000000000000000":
        output = "public contract"
    else:
        if address == from_add:
            output = "sender"
        elif address in address_dict:
            if address_dict[address]["contractCreator"] == from_add:
                output = "sender created contract"
            else:
                output = "public contract"
            if address == to_add:
                output += " receiver"
        elif address == to_add:
            output = "receiver eoa"
        else:
            output = "others"
    return output

# flatten balance change dict
def flatten(d):
    def short_key(k):
        if "_0x" in k:
            prefix, hex_part = k.split("_0x", 1)
            return prefix + "_0x" + hex_part[:8]
        return k

    def format_value(v):
        val = rounded_number(v[0])
        usd = rounded_number(v[1], usd_mode=True)
        return f"{val}" if usd == 0 else f"{val}(${usd})"

    return ';'.join(f'{short_key(k)} amount: {format_value(v)}' for k, v in d.items())

reason_message_map = {
    "detect_self_create": " The receiver contract is created by sender.",
    "sender large profit from other eoa": " Sender has profit from other address.",
    "sender large profit from contracts": " Sender has profit from public contracts.",
    "other eoa from contracts": " Another eoa profits from public contracts.",
    "senders steal token from eoa": " Sender earns tokens from other address.",
    "senders steal nfts from eoa": " Sender earns nfts from other address.",
}

# basic info to prompt
def transform_basic(folder_prefix, chain, main_token, main_token_rate):
    # transform basic information
    basic_info = collect_from_file(folder_prefix, "basic_info.json")
    tx_hash = basic_info["hash"]
    value = basic_info['value']
    output = f"This transaction is sent on {chain} blockchain"
    from_add, to_add = basic_info['from'], basic_info['to']
    if to_add != 'empty':
        output += f" by sender {shorten_address(from_add)} to receiver {shorten_address(to_add)}"
    else:
        output += f" by sender {shorten_address(from_add)} creating contracts"
    if value != 0:
        output += f" with {rounded_number(value)} {main_token} as {rounded_number(value*main_token_rate, usd_mode=True)} USD"
    output += '.'

    # transform detected reasons
    detected_reasons = basic_info["true_flags"]
    trace_reasons = basic_info["reason"]
    for reason, message in reason_message_map.items():
        if reason in detected_reasons:
            if reason == "detect_self_create":
                if to_add != 'empty':
                    output += message
            else:
                output += message
    return output, tx_hash, from_add, to_add, detected_reasons, trace_reasons


# separate balance changes to different roles
def transform_balance(tx_hash, folder_prefix, from_add, to_add):
    balance_change = collect_from_file(folder_prefix, '/token_info/balance.json')[tx_hash]
    address_dict = collect_from_file(folder_prefix, '/token_info/address_dict.json')
    sender_dict = {}
    receiver_dict = {}
    eoa_dict = {}
    contract_dict = {}
    for address in balance_change:
        # Emphasise that some addresses are special.
        role = judge_address(address, address_dict, from_add, to_add)
        token_dict = balance_change[address]
        if role == "sender":
            sender_dict[address] = token_dict
        elif "sender created contract" in role:
            sender_dict[address] = token_dict
        elif "public contract" in role:
            contract_dict[address] = token_dict
        else:
            eoa_dict[address] = token_dict
        if "receiver" in role:
            receiver_dict[address] = token_dict
    ## how to treat each group
    return balance_change, sender_dict, receiver_dict, eoa_dict, contract_dict

# balance changes to prompt
def process_balance(tx_hash, folder_prefix, from_add, to_add, reasons):
    balance_change, sender_dict, _, eoa_dict, contract_dict = transform_balance(tx_hash, folder_prefix, from_add, to_add)
    sender_sum, sender_usd_sum = sum_address_group(sender_dict)
    eoa_sum, eoa_usd_sum = sum_address_group(eoa_dict)
    contract_sum, contract_usd_sum = sum_address_group(contract_dict)
    error_rate = False
    is_nft = False
    other_type = False
    # give roles according to detected reason
    if "sender large profit from other eoa" in reasons:
        gainer = "sender"
        if len(sender_dict) > 1 or from_add not in sender_dict:
            gainer += " and his contract"
        loser = "other users"
        gainer_sum, loser_sum = sender_sum, eoa_usd_sum
    elif "sender large profit from contracts" in reasons:
        gainer = "sender"
        if len(sender_dict) > 1 or from_add not in sender_dict:
            gainer += " and his contract"
        loser = "other public contracts"
        gainer_sum, loser_sum = sender_sum, contract_usd_sum
    elif "other eoa from contracts" in reasons:
        gainer = "other user"
        loser = "other public contracts"
        gainer_sum, loser_sum = eoa_sum, contract_usd_sum
    elif "senders steal token from eoa" in reasons:
        error_rate = True
        gainer = "sender"
        if len(sender_dict) > 1 or from_add not in sender_dict:
            gainer += " and his contract"
        loser = "other users"
        gainer_sum, loser_sum = sender_sum, eoa_sum
    elif "senders steal nfts from eoa" in reasons:
        is_nft = True
        gainer = "sender"
        if len(sender_dict) > 1 or from_add not in sender_dict:
            gainer += " and his contract"
        loser = "other users"
        gainer_sum, loser_sum = sender_sum, eoa_sum
    else:
        other_type = True
        gainer, loser, gainer_sum, loser_sum = None, None, 0, 0
    if not other_type:
        if is_nft:
            balance_prompt = f"{gainer} collect nft as {flatten(gainer_sum)} from {loser}."
        elif error_rate:
            balance_prompt = f"{gainer} collect large amount unknown tokens as {flatten(gainer_sum)} from {loser} as {flatten(eoa_sum)}."
        else:
            balance_prompt = f"{gainer} collect high value tokens as {flatten(gainer_sum)} from {loser} losing {rounded_number(loser_sum, usd_mode=True)} USD."
    else:
        balance_prompt = f"senders: {flatten(sender_sum)}, other users: {flatten(eoa_sum)}, public contracts: {flatten(contract_sum)}."
    return balance_prompt, sender_dict, eoa_dict, contract_dict

# Collect trace into two dicts
def transform_trace(tx_hash, folder_prefix):
    call_dict = {}
    event_dict = {}
    trace = collect_from_file(folder_prefix, '/invocation_tree/decode_trace_' + tx_hash + '.json')
    for t in trace:
        if 'call' in t['type']:
            call_key = t["to"]
            add_to_key_list_dict(call_dict, call_key, t)

        # Adding event to its original call for LLM comprehension
        elif 'event' in t['type']:
            if not is_hex64(t['function']):
                event_key = t["address"]
                add_to_key_list_dict(event_dict, event_key, t)
    return call_dict, event_dict

# trace to prompt
def process_trace(tx_hash, folder_prefix, to_address, sender_dict, contract_dict, detect_flags, rule_reasons, token_left):
    call_collect, event_collect = transform_trace(tx_hash, folder_prefix)
    trace_prompt = ""

    # transform trace related reasons
    if 'rule_detection_result' in detect_flags:
        if 'Suspicious Flashloan Attack Detected' in rule_reasons:
            trace_prompt += " Transaction has suspicious flash loan usage."
        if 'Token Supply Abrupt Changes Detected' in rule_reasons:
            trace_prompt += " Total supply of related token changed."
        if 'Suspicious Reentrancy Attack Detected' in rule_reasons:
            trace_prompt += " There are repeated calls indicating reentrancy attack."

    # transform counts of calls and events of important addresses to prompt
    trace_prompt += " The summary of calls and events of important addresses:"
    balanced_prompt = trace_prompt
    if to_address in call_collect:
        trace_prompt += f" {shorten_address(to_address)} called: {count_names(call_collect[to_address], "functionName")}"
        if to_address in event_collect:
            trace_prompt += f", emitting events: {count_names(event_collect[to_address], "function")};"
        else:
            trace_prompt += ";"
    shortened_prompt = trace_prompt
    for sender_address in sender_dict:
        if sender_address in call_collect:
            trace_prompt += f" {shorten_address(sender_address)} called: {count_names(call_collect[sender_address], "functionName")}"
            if sender_address in event_collect:
                trace_prompt += f", emitting events: {count_names(event_collect[sender_address], "function")};"
            else:
                trace_prompt += ";"
    for contract_address in  contract_dict:
        if contract_address in call_collect:
            trace_prompt += f" {shorten_address(contract_address)} called: {count_names(call_collect[contract_address], "functionName")}"
            if contract_address in event_collect:
                trace_prompt += f", emitting events: {count_names(event_collect[contract_address], "function")};"
            else:
                trace_prompt += ";"
    # if trace prompt is too short
    if count_tokens(trace_prompt) < count_tokens(balanced_prompt) + 50:
        for c_address in call_collect:
            balanced_prompt += f" {shorten_address(c_address)} called: {count_names(call_collect[c_address], "functionName")}"
            if c_address in event_collect:
                balanced_prompt += f", emitting events: {count_names(event_collect[c_address], "function")};"
        if count_tokens(balanced_prompt) < token_left:
            trace_prompt = balanced_prompt

    # if trace prompt is too long
    elif count_tokens(trace_prompt) > token_left:
        # Only keep the 3 largest function count contract addresses
        def count_total_calls(addr):
            return sum(count_names(call_collect[addr], 'functionName').values())

        top_contracts = sorted(
            [addr for addr in contract_dict if addr in call_collect],
            key=count_total_calls,
            reverse=True
        )[:1]

        trace_prompt = shortened_prompt
        for contract_address in top_contracts:
            trace_prompt += f" {shorten_address(contract_address)} called: {count_names(call_collect[contract_address], 'functionName')}"
            if contract_address in event_collect:
                trace_prompt += f", emitting events: {count_names(event_collect[contract_address], 'function')};"
            else:
                trace_prompt += ";"

    return trace_prompt

# combine three text in a json
def generate_output(folder_prefix, chain, main_token):
    token_rates = collect_from_file(folder_prefix, '/token_info/rate_dict.json')
    main_token_rate = token_rates[main_token] if main_token in token_rates else 0
    basic_prompt, tx_hash, from_add, to_add, detected_reasons, trace_reasons = transform_basic(folder_prefix, chain, main_token, main_token_rate)
    balance_prompt, sender_dict, _, contract_dict = process_balance(tx_hash, folder_prefix, from_add, to_add, detected_reasons)
    token_left = 450 - count_tokens(basic_prompt) - count_tokens(balance_prompt)
    trace_prompt = process_trace(tx_hash, folder_prefix, to_add, sender_dict, contract_dict, detected_reasons, trace_reasons, token_left)
    return {"basic": basic_prompt, "balance": balance_prompt, "trace": trace_prompt}

