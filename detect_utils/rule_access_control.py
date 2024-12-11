from detect_utils.tools import collect_from_file, filter_transaction

# Detect whether all calls with state changes have at least a parent with check_opcodes as True
def check_all_parents(state_changed_list, trace_dict):
    key_dict = {}
    limit = 1
    for key in state_changed_list:
        error_sum = 0
        parent = key
        key_dict[key] = True
        while isinstance(parent, int):
            if parent not in trace_dict:
                if error_sum < limit:
                    error_sum += 1
                else:
                    key_dict[key] = False
                    break
            else:
                if not trace_dict[parent]['callerchecked']:
                    if error_sum < limit:
                        error_sum += 1
                    else:
                        key_dict[key] = False
                        break
                parent = trace_dict[parent]['parent']
    return key_dict

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
            state_changed = False
            for change in t['statechanges']:
                if change['reason'] == 'SSTORE':
                    state_changed = True
                    break
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
    result = check_all_parents(state_changed_list, trace_dict)

    if len(state_changed_list) == 0:
        possible_hack = False
    else:
        if sum(result.values()) / len(state_changed_list) > 0.5:
            possible_hack = False
        else:
            possible_hack = True
    return possible_hack
