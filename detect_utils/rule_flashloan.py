from detect_utils.tools import collect_from_file, filter_transaction, check_balance


def has_flashloan(tx_hash, chain):
    trace = collect_from_file(tx_hash, chain, '/invocation_tree/decode_trace_' + tx_hash + '.json')

    address_list = []

    for element in trace:
        if element['type'] == 'event' and element['function'].lower() == 'flashloan':
            if len(element['input']) > 0:
                value = element['input'][0].lower()
                if (isinstance(value, str) and len(value) == 42
                        and value.startswith("0x") and value not in address_list):
                    address_list.append(value)
        else:
            pass

    if len(address_list) > 0:
        print('Flashloan Event Detected')

    return address_list


def detect_flashloan_transaction(tx_hash, chain):
    basic_info = collect_from_file(tx_hash, chain, '/basic_info.json')

    address_list = has_flashloan(tx_hash, chain)

    if not filter_transaction(basic_info):
        return False

    elif len(address_list) == 0:
        return False

    else:
        possible_hack = False

        address_list.append(basic_info['from'])
        address_list.append(basic_info['to'])
        for address in address_list:
            if check_balance(tx_hash, chain, address):
                possible_hack = True

        return possible_hack
