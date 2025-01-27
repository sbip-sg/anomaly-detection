from detect_utils.tools import collect_from_file
from utils.collect_transfer import find_address_transfer_event
import json

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
    outputs = {'transactionHash': tx_hash, 'chain': chain, 'value': basic_info['value'],
               'gasUsed': basic_info['gasUsed'], 'fromAddress': shorten_address(basic_info['from']), 'toAddress': shorten_address(basic_info['to'])}
    return outputs

def get_sub_output(t, call_key):
    sub_output = {'call_index': call_key, 'function': t["function"], 'fromAddress': shorten_address(t['from']), 'toAddress': shorten_address(t['to']), 'callType': t['type'],
                  'output': t["output"]}
    # sub_output['parameters'] = t['parameters']
    if t['statechanges']:
        sub_output['stateChanges'] = t['statechanges']
    if t["value"] != 0 and t['status'] != "OutOfGas":
        amount = t["value"] / 1e18
        sub_output['ETHSending'] = amount
    return sub_output

def collect_event(t, currency_dict):
    event_name = t['function']
    topics = t['input']
    event_data = t['data']
    event_output = {'eventName': t["function"], 'contractAddress': shorten_address(t['address']), 'data': t['data']}
    # sub_output['topics'] = t['topics']
    if event_name.lower() == 'transfer' and len(topics) != 0:
        transfer_from, transfer_to, amount = find_address_transfer_event(t, topics)
        if isinstance(amount, int):
            if t['address'] in currency_dict:
                (currency, decimal, exchange_rate) = currency_dict[t['address']]
            else:
                (currency, decimal, exchange_rate) = (t['address'], 0, 0)

            value = amount / pow(10, decimal)
            event_output['transfer'] = {'fromAddress': shorten_address(transfer_from), 'toAddress': shorten_address(transfer_to),'currency': currency,'value': value}
            if exchange_rate != 0:
                event_output['transfer']['USDValue'] = rounded_number(value * exchange_rate)

    elif event_name.lower() == 'withdrawal' and event_data and topics and t[
        'address'].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
        withdrawal_address = topics[0]
        if len(event_data) == 2:
            amount = event_data[1]
        else:
            amount = event_data[0]
        if isinstance(amount, int):
            event_output['withdrawal'] = {'withdrawAddress': shorten_address(withdrawal_address), 'value': amount / 1e18}
    elif event_name.lower() == 'deposit' and event_data and topics and t[
        'address'].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
        deposit_address = topics[0]
        if len(event_data) == 2:
            amount = event_data[1]
        else:
            amount = event_data[0]
        if isinstance(amount, int):
            event_output['deposit'] = {'depositAddress': shorten_address(deposit_address), 'value': amount / 1e18}
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
            calls[call_key] = get_sub_output(t, call_key)
        elif 'event' in t['type']:
            parent = t['parent']
            if parent in calls:
                if 'events' not in calls[parent]:
                    calls[parent]['events'] = [collect_event(t, currency_dict)]
                else:
                    calls[parent]['events'].append(collect_event(t, currency_dict))
        elif 'create' in t['type']:
            calls['c' + str(c_index)] = {'type': 'create', 'fromAddress': shorten_address(t["from"]),
                                    'createdAddress': shorten_address(t['to']),'value': t["value"], 'data': t['data']}
            c_index += 1
        elif 'selfdestruct' in t['type']:
            calls['d' + str(d_index)] = {'type': 'self-destruct', 'address': shorten_address(t["address"]),
                                    'refundAddress': shorten_address(t['refund_target']),'value': t["value"]}
            d_index += 1
    return calls

def generate_balance(token: str, value: float, usd_amount: float):
    known = not token.startswith('0x')
    use_usd = usd_amount != 0
    if not known:
        token = shorten_address(token)
    token_output = {'known': known, 'token': token, 'value': value}
    if use_usd:
        token_output['USDValue'] = rounded_number(usd_amount)
    return token_output

def transform_balance(tx_hash, chain):
    balance_change = collect_from_file(tx_hash, chain, '/token_info/balance.json')[tx_hash]
    outputs = {}
    for address in balance_change:
        balance_list = []
        token_dict = balance_change[address]
        if shorten_address(address) not in outputs:
            address = shorten_address(address)
        for token in token_dict:
            value, usd_amount = token_dict[token]
            try:
                balance_list.append(generate_balance(token, value, usd_amount))
            except Exception:
                print('token info exception')
        outputs[address] = balance_list
    return outputs

def generate_output(tx_hash, chain, folder_prefix):
    basic_info = transform_basic(tx_hash, chain)
    call_dict = transform_trace(tx_hash, chain)
    balance_output = transform_balance(tx_hash, chain)
    result = {'transactionInfo': basic_info, 'trace': call_dict, 'balanceChanges': balance_output}
    with open(folder_prefix + f"/output_{tx_hash}.json", "w") as json_file:
        json.dump(result, json_file, indent = 2)
    return True

