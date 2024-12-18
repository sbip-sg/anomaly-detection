from detect_utils.tools import collect_from_file
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('http://sbip-g3.d2.comp.nus.edu.sg:8545'))

def collect_idx(tx_hash, chain):
    trace = collect_from_file(tx_hash, chain, '/trace_json/trace_' + tx_hash + '.json')
    rate_dict = collect_from_file(tx_hash, chain, '/token_info/rate_dict.json')
    currency_dict = collect_from_file(tx_hash, chain, '/token_info/currency_dict.json')
    idx_dict = {}
    parent_dict = {}
    event_parent_dict = {}
    if not check_balance(tx_hash, chain, -10000):
        return idx_dict

    for element in trace:
        if 'call' in element['kind']:
            call_idx = element['call_idx']
            event_parent_dict[element['depth']] = element['parent']
            is_delegate = element['kind'] == 'delegatecall'
            if element['parent'] in parent_dict and parent_dict[element['parent']][1]:
                true_parent = parent_dict[element['parent']][0]
                parent_dict[call_idx] = [true_parent, is_delegate]
            else:
                parent_dict[call_idx] = [element['parent'], is_delegate]
        usd_value = 0
        if element['kind'] == 'call' and element['value'][3:]:
            call_idx = element['call_idx']
            amount = int(element['value'][2:], 16)
            if 'ETH' in rate_dict:
                try:
                    usd_value = rate_dict['ETH'] * amount / pow(10, 18)
                except:
                    usd_value = 20000
            checked_idx = parent_dict[call_idx][0]
            if checked_idx not in idx_dict and isinstance(checked_idx, int):
                idx_dict[checked_idx] = usd_value

        elif element['kind'] == 'event' and element['decoded']['name']:
            event_name = element['decoded']['name'].lower()
            depth = element['depth'] - 1
            if event_name == 'transfer' and depth in event_parent_dict:
                address = element['from']
                if address in rate_dict:
                    decimal = 0
                    rate = rate_dict[address]
                elif address in currency_dict:
                    decimal = currency_dict[address][1]
                    rate =  currency_dict[address][2]
                else:
                    decimal = 0
                    rate = 0
                data = element['raw']['data'][2:]
                if data:
                    amount = int(data, 16)
                else:
                    amount = int(element['raw']['topics'][-1][2:], 16)
                try:
                    usd_value = rate * amount / pow(10, decimal)
                except:
                    usd_value = 20000
            checked_idx = event_parent_dict[depth]
            if checked_idx not in idx_dict and isinstance(checked_idx, int):
                idx_dict[checked_idx] = usd_value
            if checked_idx in parent_dict and parent_dict[checked_idx][0] not in idx_dict and isinstance(
                    parent_dict[checked_idx][0], int):
                idx_dict[parent_dict[checked_idx][0]] = usd_value
    return idx_dict



# There is any 57(JUMPI) after 33(CALLER)
def check_opcodes(code_list):
    if "33" not in code_list:
        return False
    caller_index = code_list.index("33")
    if "57" in code_list[caller_index:]:
        return True
    return False

# Detect the balance change of given address of a transaction
def check_balance(tx_hash, chain, value):
    balance_change = collect_from_file(tx_hash, chain, '/token_info/balance.json')
    if balance_change:
        balance_change = balance_change[tx_hash]
        for address in balance_change:
            address_balance_change = balance_change.get(address)
            address_usd_change = 0
            for token in address_balance_change:
                address_usd_change += address_balance_change[token][1]
            if address_usd_change < value:
                return True
    return False

# Detector containing two checks to be considered as possible hack:
# Detector containing two checks to be considered as possible hack:
def detect_access_control(tx_hash, chain):
    idx_dict = collect_idx(tx_hash, chain)
    skiplist = ['swap', 'transferfrom', 'deposit', 'withdraw', 'flashloan', 'receiveflashloan', 'transfer'
                , 'multicall', 'swapuniv2', 'execute', 'fallback', 'mint', 'swapcallback', 'wrapall', 'sweeptoken'
               ,'patchsequence', 'swapexactytfortoken', 'exectransaction']

    trace = collect_from_file(tx_hash, chain, '/trace_json/trace_' + tx_hash + '.json')
    sum_value = 0
    sum_all_value = sum(idx_dict.values())
    for t in trace:
        if 'call' in t['kind'] and t['call_idx'] in idx_dict:
            opcodes = t['opcodes']
            if t['decoded']['call_data']:
                name = t['decoded']['call_data']['signature'].lower().split('(')[0]
                if name in skiplist:
                    continue
            if not check_opcodes(opcodes):
                if sum_all_value > 500000:
                    return True
                sum_value += idx_dict[t['call_idx']]
    if sum_value > 20000 and sum_all_value > 40000:
        return True
    return False
