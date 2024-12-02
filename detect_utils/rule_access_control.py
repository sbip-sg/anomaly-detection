from detect_utils.tools import collect_from_file, filter_transaction

# Detect whether all calls with state changes have at least a parent with check_opcodes as True
def check_all_parents(state_changed_list, trace_dict):
    for key in state_changed_list:
        parent = key
        while isinstance(parent, int):
            if parent not in trace_dict:
                return False
            if trace_dict[parent]['callerchecked']:
                break
            parent = trace_dict[parent]['parent']
            if not isinstance(parent, int):
                return False
    return True

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
    basic_info = collect_from_file(tx_hash, chain, '/basic_info.json')
    if not filter_transaction(basic_info):
        return False
    trace_dict = {}
    state_changed_list = []
    
    trace = collect_from_file(tx_hash, chain, '/trace_json/trace_' + tx_hash + '.json')
    for t in trace:
        if 'call' in t['kind']:
            state_changed = bool(t['statechanges'])
            if state_changed:
                state_changed_list.append(t['call_idx'])
            parent = t['parent']
            children = t['children']
            opcodes = t['opcodes']
            trace_dict[t['call_idx']] = {
                'statechanged': state_changed,
                'parent': parent,
                'children': children,
                'opcodes': opcodes,
                'callerchecked': check_opcodes(opcodes)
            }
    possible_hack = not check_all_parents(state_changed_list, trace_dict)
    return possible_hack
