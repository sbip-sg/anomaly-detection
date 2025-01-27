from detect_utils.tools import collect_from_file
from utils.collect_transfer import find_address_transfer_event

def rounded_number(number):
    return round(number, 2)

def shorten_address(address):
    if isinstance(address, str):
        if address.startswith('0x') and len(address) == 42:
            return address[:10]
        else:
            return address
    else:
        raise TypeError('Non-string as address')

def transform_basic(tx_hash, chain):
    basic_info = collect_from_file(tx_hash, chain, '/basic_info.json')
    output = ""
    value = basic_info['value']
    if value == 0:
        output += "This transaction has no eth transfer value, "
    else:
        output += f"This transaction is sent with {value} eth, "

    gas_usage = basic_info['gasUsed']
    output += f"used {gas_usage} gas. "

    from_add, to_add = basic_info['from'], basic_info['to']

    output += f"The sender is {shorten_address(from_add)} and the receiver is {shorten_address(to_add)}.\n"
    return output, from_add, to_add

def get_sub_output(t):
    sub_output = f"{shorten_address(t['from'])} calls {t["function"]} of {shorten_address(t['to'])}"
    inputs = t["input"]
    #if inputs:
    #    sub_output += f" with parameters {str(inputs)}"
    f_outputs = t["output"]
    if f_outputs:
        sub_output += f" output {str(f_outputs)}"
    if t['type'] != 'call':
        sub_output += f" as a {t['type']}"
    sub_output += ". "
    if t['statechanges']:
        sub_output += f"Contract states are changed as:"
        for change in t['statechanges']:
            if change['reason'] == "SLOAD":
                sub_output += f" load {change['value']} in {change['key']},"
            elif change['reason'] == "SSTORE":
                sub_output += f" store {change['value']} over {change['had_value']} in {change['key']},"
        sub_output = sub_output[:-1] + '.'
    if t["value"] != 0 and t['status'] != "OutOfGas":
        amount = t["value"] / 1e18
        sub_output += f"{shorten_address(t['from'])} sends {str(amount)} ETH to {shorten_address(t['to'])}."
    return sub_output

def collect_event(t, currency_dict):
    event_name = t['function']
    topics = t['input']
    event_data = t['data']
    event_output = f' Generate {t['function']} event from {shorten_address(t['address'])}'
    if topics:
        event_output += f" with topics {str(topics)}"
    if event_data:
        event_output += f" output data {str(event_data)}"
    event_output += '.'
    if event_name.lower() == 'transfer' and len(topics) != 0:
        transfer_from, transfer_to, amount = find_address_transfer_event(t, topics)
        if isinstance(amount, int):
            if t['address'] in currency_dict:
                (currency, decimal, exchange_rate) = currency_dict[t['address']]
            else:
                (currency, decimal, exchange_rate) = (t['address'], 0, 0)
            if decimal != 0:
                value = amount / pow(10, decimal)
                event_output += f' Transfer {str(value)} {currency} from {shorten_address(transfer_from)} to {shorten_address(transfer_to)}'
                if exchange_rate != 0:
                    event_output += f' in {str(rounded_number(value * exchange_rate))} USD'
            else:
                event_output += f' Transfer unknown {currency} in {amount} from {shorten_address(transfer_from)} to {shorten_address(transfer_to)}'
            event_output += '.'
    elif event_name.lower() == 'withdrawal' and event_data and topics and t[
        'address'].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
        withdrawal_address = topics[0]
        if len(event_data) == 2:
            amount = event_data[1]
        else:
            amount = event_data[0]
        if isinstance(amount, int):
            event_output += f' {shorten_address(withdrawal_address)} withdraws {str(amount / 1e18)} ETH from Wrapped ETH.'
    elif event_name.lower() == 'deposit' and event_data and topics and t[
        'address'].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
        deposit_address = topics[0]
        if len(event_data) == 2:
            amount = event_data[1]
        else:
            amount = event_data[0]
        if isinstance(amount, int):
            event_output += f' {shorten_address(deposit_address)} deposits {str(amount / 1e18)} ETH to Wrapped ETH.'
    return event_output

def transform_trace(tx_hash, chain):
    trace = collect_from_file(tx_hash, chain, '/invocation_tree/decode_trace_' + tx_hash + '.json')
    currency_dict = collect_from_file(tx_hash, chain, '/token_info/currency_dict.json')
    calls = {}
    c_index = 0
    d_index = 0
    for t in trace:
        if 'call' in t['type']:
            call_key = t["call_idx"]
            calls[call_key] = get_sub_output(t)
        elif 'event' in t['type']:
            parent = t['parent']
            if parent in calls:
                calls[parent] += collect_event(t, currency_dict)
        elif 'create' in t['type']:
            calls['c' + str(c_index)] = f'{shorten_address(t["from"])} creates {shorten_address(t['to'])} funding {str(t["value"]/ 1e18)} ETH with {t['data']}'
            c_index += 1
        elif 'selfdestruct' in t['type']:
            calls['d' + str(d_index)] = f'{shorten_address(t["address"])} self-destructs refunding {str(t["value"]/ 1e18)} ETH to {shorten_address(t["refund_target"])}'
            d_index += 1
    return calls

def generate_balance(token: str, value: float, usd_amount: float):
    known = not token.startswith('0x')
    use_usd = usd_amount != 0
    token_output = ""
    if value >= 0:
        token_output += "Gain"
    else:
        token_output += "Lose"
    if not known:
        token_output += " unknown"
    token_output += f" {token} in amount {abs(value)}"
    if use_usd:
        token_output += f" as {rounded_number(abs(usd_amount))} USD"
    return token_output + '. '

def transform_balance(tx_hash, chain, from_add, to_add):
    balance_change = collect_from_file(tx_hash, chain, '/token_info/balance.json')[tx_hash]
    outputs = []
    for address in balance_change:
        if address == from_add:
            address_info = f"The balance change of sender {shorten_address(address)}:"
        elif address == to_add:
            address_info = f"The balance change of receiver {shorten_address(address)}:"
        else:
            address_info = f"The balance change of {shorten_address(address)}:"
        token_dict = balance_change[address]
        for token in token_dict:
            value, usd_amount = token_dict[token]
            try:
                token_output = generate_balance(token, value, usd_amount)
            except Exception:
                print('token info exception')
                token_output = ''
            address_info += token_output
        outputs.append(address_info)
    return outputs

def generate_output(tx_hash, chain, folder_prefix):
    basic_info, from_add, to_add = transform_basic(tx_hash, chain)
    call_dict = transform_trace(tx_hash, chain)
    result = basic_info + "The call trace and events are listed below,\n" + "\n".join(str(value) for value in call_dict.values())
    balance_output = transform_balance(tx_hash, chain, from_add, to_add)
    if balance_output:
        result += "\nThe balance changes are listed below,\n" + "\n".join(balance_output)
    with open(folder_prefix + "/output.txt", "w") as file:
        file.write(result)
    return True

