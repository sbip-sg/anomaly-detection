from detect_utils.tools import collect_from_file, filter_transaction

def collect_idx(tx_hash, chain):
    trace = collect_from_file(tx_hash, chain, '/trace_json/trace_' + tx_hash + '.json')

    idx_list = []
    relation_dict = {}

    for element in trace:
        if 'call' in element['kind']:
            relation_dict[element['call_idx']] = element['parent']
        elif element['kind'] == 'event' and element['decoded']['name']:
            event_name = element['decoded']['name'].lower()
            if event_name == 'transfer' and relation_dict[element['parent']] not in idx_list:
                if element['parent'] in relation_dict:
                    idx_list.append(relation_dict[element['parent']])
    return idx_list

# There is any 57(JUMPI) after 33(CALLER)
def check_opcodes(code_list):
    if "33" not in code_list:
        return False
    caller_index = code_list.index("33")
    if "57" in code_list[caller_index:]:
        return True
    return False


# Detector containing two checks to be considered as possible hack:
def detect_access_control(tx_hash, chain):

    idx_list = collect_idx(tx_hash, chain)

    skiplist = ['swap', 'transferfrom', 'deposit', 'withdraw', 'flashloan', 'receiveflashloan', 'transfer']

    trace = collect_from_file(tx_hash, chain, '/trace_json/trace_' + tx_hash + '.json')
    for t in trace:
        if 'call' in t['kind'] and t['call_idx'] in idx_list:
            opcodes = t['opcodes']
            name = t['decoded']['call_data']['signature'].lower().split('(')[0]
            if name in skiplist:
                continue
            if not check_opcodes(opcodes):
                return True
