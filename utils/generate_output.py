from detect_utils.tools import collect_from_file
from utils.collect_transfer import find_address_transfer_event
import json
import tiktoken

def count_tokens(text, model="o1-"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

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
            return round(number, 2)
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
                result = address[-10:]
            return result
        else:
            return address
    else:
        raise TypeError('Non-string as address')

# Basic information to text
def transform_basic(folder_prefix, chain, main_token, main_token_rate):
    basic_info = collect_from_file(folder_prefix, '/basic_info.json')
    value = basic_info['value']
    output = f"This transaction is sent with {rounded_number(value)} {main_token} on {chain} blockchain"
    if value != 0:
        output += f" as {rounded_number(value*main_token_rate, usd_mode=True)} USD"
    output += ', '


    gas_usage = basic_info['gasUsed']
    output += f"used {gas_usage} gas. "

    from_add, to_add = basic_info['from'], basic_info['to']

    output += f"The sender is {shorten_address(from_add)} and the receiver is {shorten_address(to_add)}."
    # Deliver addresses to balance changes
    return output, from_add, to_add

def flatten(nested_list):
    """Flattens a nested list into a single list."""
    flat_list = []

    def recurse(sublist):
        for item in sublist:
            if isinstance(item, list):
                recurse(item)
            else:
                flat_list.append(item)

    recurse(nested_list)
    return flat_list

def deal_input(input_string):
    if not isinstance(input_string, str):
        try:
            input_string = str(input_string)
        except Exception as e:
            raise ValueError(f"An value error occurred in inputs: {e}")
    if input_string.startswith('0x') and len(input_string) == 42:
        input_string = shorten_address(input_string)
    elif input_string.startswith('0x') and len(input_string) > 20:
        input_string = '[bytes]'
    return input_string


def process_inputs(inputs):
    flatten_inputs = flatten(inputs)
    processed_inputs = [deal_input(item) for item in flatten_inputs]
    return " ".join(processed_inputs)  # Join into a single string

# Transform a call to text
def get_sub_output(t, main_token, main_token_rate):
    sub_output = f"{shorten_address(t['from'])} calls {t["function"]} of {shorten_address(t['to'])}"
    inputs = t["input"]
    if inputs:
        sub_output += f" with parameters {process_inputs(inputs)}"
    f_outputs = [str(out_item) for out_item in t["output"]]
    if f_outputs:
        sub_output += f" output {" ".join(flatten(f_outputs))}"
    # Delegate call and static call
    if t['type'] != 'call':
        sub_output += f" as a {t['type']}"
    sub_output += "."
    # Add state changes
    #if t['statechanges']:
    #    sub_output += f" Contract states are changed as:"
    #    for change in t['statechanges']:
    #        # Explain sload and sstore
    #        if change['reason'] == "SLOAD":
    #            sub_output += f" load {change['value']} in {change['key']},"
    #        elif change['reason'] == "SSTORE":
    #            sub_output += f" store {change['value']} over {change['had_value']} in {change['key']},"
    #    sub_output = sub_output[:-1] + '.'
    # Value means having ETH transferring
    if t["value"] != 0 and t['status'] != "OutOfGas":
        amount = rounded_number(t["value"] / 1e18)
        usd_amount = rounded_number(t["value"] / 1e18 * main_token_rate, usd_mode=True)
        sub_output += f"{shorten_address(t['from'])} sends {amount} {main_token} as {usd_amount} USD to {shorten_address(t['to'])}."
    return sub_output

# Transform an event to text
def collect_event(t, currency_dict, chain, main_token_rate):
    event_name = t['function']
    topics = t['input']
    event_data = t['data']
    event_output = f' Generate {t['function']} event from {shorten_address(t['address'])}'
    if topics:
        event_output += f" with topics {process_inputs(topics)}"
    if event_data:
        event_output += f" output data {process_inputs(event_data)}"
    event_output += '.'
    # When this event shows transferring tokens
    if event_name.lower() == 'transfer' and len(topics) != 0:
        transfer_from, transfer_to, amount = find_address_transfer_event(t, topics)
        if isinstance(amount, int):
            if t['address'] in currency_dict:
                (currency, decimal, exchange_rate) = currency_dict[t['address']]
            else:
                (currency, decimal, exchange_rate) = (t['address'], 0, 0)
            if decimal != 0:
                value = amount / pow(10, decimal)
                event_output += f' Transfer {rounded_number(value)} {currency} from {shorten_address(transfer_from)} to {shorten_address(transfer_to)}'
                if exchange_rate != 0:
                    event_output += f' as {rounded_number(value * exchange_rate, usd_mode=True)} USD'
            else:
                event_output += f' Transfer unknown {currency} in {amount} from {shorten_address(transfer_from)} to {shorten_address(transfer_to)}'
            event_output += '.'
    # Special case: withdraw from Wrapped ETH (withdraw eth by sending WETH)
    # Adding information since no token flow related call or event is here
    if chain == 'eth':
        if event_name.lower() == 'withdrawal' and event_data and topics and t[
            'address'].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
            withdrawal_address = topics[0]
            if len(event_data) == 2:
                amount = event_data[1]
            else:
                amount = event_data[0]
            if isinstance(amount, int):
                event_output += f' {shorten_address(withdrawal_address)} withdraws {rounded_number(amount / 1e18)} ETH as {rounded_number(main_token_rate * amount / 1e18, usd_mode=True)} USD from Wrapped ETH.'
        # Special case: deposit to Wrapped ETH (deposit eth and receive WETH), similar to above one
        elif event_name.lower() == 'deposit' and event_data and topics and t[
            'address'].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
            deposit_address = topics[0]
            if len(event_data) == 2:
                amount = event_data[1]
            else:
                amount = event_data[0]
            if isinstance(amount, int):
                event_output += f' {shorten_address(deposit_address)} deposits {rounded_number(amount / 1e18)} ETH as {rounded_number(main_token_rate * amount / 1e18, usd_mode=True)} USD to Wrapped ETH.'
    return event_output

# Trace to text
def transform_trace(tx_hash, folder_prefix, main_token, chain, main_token_rate):
    trace = collect_from_file(folder_prefix, '/invocation_tree/decode_trace_' + tx_hash + '.json')
    currency_dict = collect_from_file(folder_prefix, '/token_info/currency_dict.json')
    calls = {}
    c_index = 0
    d_index = 0
    for t in trace:
        if 'call' in t['type']:
            call_key = t["call_idx"]
            calls[call_key] = get_sub_output(t, main_token, main_token_rate)

        # Adding event to its original call for LLM comprehension
        elif 'event' in t['type']:
            parent = t['parent']
            if parent in calls:
                calls[parent] += collect_event(t, currency_dict, chain, main_token_rate)
        elif 'create' in t['type']:
            c_value = rounded_number(t["value"]/ 1e18)
            USD_value = rounded_number(main_token_rate * t["value"] / 1e18, usd_mode=True)
            calls['c' + str(c_index)] = f'{shorten_address(t["from"])} creates {shorten_address(t['to'])} funding {c_value} {main_token} as {USD_value} USD.'
            c_index += 1
        elif 'selfdestruct' in t['type']:
            d_value = rounded_number(t["value"]/ 1e18)
            USD_value = rounded_number(main_token_rate * t["value"] / 1e18, usd_mode=True)
            calls['d' + str(d_index)] = f'{shorten_address(t["address"])} self-destructs refunding {d_value} {main_token} as {USD_value} USD to {shorten_address(t["refund_target"])}.'
            d_index += 1
    return calls

# Single balance change to text
def generate_balance(token: str, value: float, usd_amount: float):
    known = not token.startswith('0x')
    use_usd = usd_amount != 0
    # Confirm AI knowing this is the change
    output_value = rounded_number(value)
    token_output = f"+{output_value}" if value >= 0 else f"{output_value}"
    # Inform AI that this token is not known.
    token_output += f" unknown {shorten_address(token)}" if not known else f" {token}"
    # If we know the USD value of this change.
    if use_usd:
        token_output += f" as {rounded_number(abs(usd_amount), usd_mode=True)} USD"
    return token_output + '. '

# balance changes to text
def transform_balance(tx_hash, folder_prefix, from_add, to_add):
    balance_change = collect_from_file(folder_prefix, '/token_info/balance.json')[tx_hash]
    outputs = []
    for address in balance_change:
        # Emphasise that some addresses are special.
        role = {
            from_add: " sender",
            to_add: " receiver"
        }.get(address, "")

        address_info = f"The balance change of{role} {shorten_address(address)}:"
        token_dict = balance_change[address]
        for token in token_dict:
            value, usd_amount = token_dict[token]
            try:
                token_output = generate_balance(token, value, usd_amount)
            except Exception as e:
                print('token info exception:', e)
                token_output = ''
            address_info += token_output
        outputs.append(address_info)
    return outputs

# combine three text in a json
def generate_output(tx_hash, chain, folder_prefix, main_token):
    rate_dict = collect_from_file(folder_prefix, '/token_info/rate_dict.json')
    if main_token in rate_dict:
        main_token_rate = rate_dict[main_token]
    else:
        main_token_rate = 0
    basic_info, from_add, to_add = transform_basic(folder_prefix, chain, main_token, main_token_rate)
    call_dict = transform_trace(tx_hash, folder_prefix, main_token, chain, main_token_rate)
    balance_output = transform_balance(tx_hash, folder_prefix, from_add, to_add)
    trace = "\n ".join(str(value) for value in call_dict.values())
    balances = "\n ".join(balance_output)

    trace_size = count_tokens(trace)
    balance_size = count_tokens(balances)
    if trace_size + balance_size > 40000:
        limit = 80000 - len(basic_info) - len(balances)
        trace = trace[:limit]
        if balance_size < 40000:
            while count_tokens(trace) > 40000 - balance_size:
                trace = trace[:-4000]

    result_dict = {"transactionInfo": basic_info, "trace": trace, "balanceChanges": balances}

    with open(folder_prefix + f"/output_{tx_hash}.json", "w") as json_file:
        json.dump(result_dict, json_file, indent = 2)
    return True

