from detect_utils.tools import collect_from_file, filter_transaction, check_balance

def calc_ratio(numbers):
    if not numbers:  # Check for empty list
        return None  # Return None or raise an error if needed
    largest = max(numbers)
    smallest = min(numbers)
    return (largest - smallest) / largest

# Detect whether the trace of a transaction has event named flashloan and return the receiver address list
def total_supply(tx_hash, chain):
    trace = collect_from_file(tx_hash, chain, '/invocation_tree/decode_trace_' + tx_hash + '.json')

    total_supply = {}

    for element in trace:
        if element['type'].lower() == 'call' or element['type'] == 'staticcall':
            element_name = element['functionName'].lower()
            if 'totalsupply' in element_name  and len(element['output']) > 0:
                if isinstance(element['output'][0], int):
                    if element_name not in total_supply:
                        total_supply[element_name] = {}
                    if element['to'] not in total_supply[element_name]:
                        total_supply[element_name][element['to']] = []
                    total_supply[element_name][element['to']].append(element['output'][0])
        else:
            pass

    # Apply calc_ratio
    for n in total_supply:
        for address in total_supply[n]:
            # Apply calc_ratio to the list of values
            total_supply[n][address] = calc_ratio(total_supply[n][address])

    # Cleanup logic: Remove zero values and empty addresses
    for n in list(total_supply.keys()):  # Use list to allow modification during iteration
        for address in list(total_supply[n].keys()):
            # Check if the calculated ratio is zero
            if total_supply[n][address] == 0 or total_supply[n][address] is None:
                del total_supply[n][address]  # Remove the address
        # Remove function name if it has no addresses left
        if not total_supply[n]:
            del total_supply[n]

    return total_supply


def find_largest_number(d):
    largest = float('-inf')  # Start with the smallest possible value
    stack = [d]  # Use a stack for recursive-like traversal

    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            stack.extend(current.values())  # Add nested dictionaries to the stack
        elif isinstance(current, (int, float)):  # Check for numeric values
            largest = max(largest, current)  # Compare numeric values
    return largest

# Detect whether a transaction has high range of total supply changes.
def detect_token_supply(tx_hash, chain):
    basic_info = collect_from_file(tx_hash, chain, '/basic_info.json')

    total_supply_dict = total_supply(tx_hash, chain)

    basic_info = collect_from_file(tx_hash, chain, '/basic_info.json')
    trace = collect_from_file(tx_hash, chain, '/invocation_tree/decode_trace_' + tx_hash + '.json')

    # Gas usage not passed
    if not filter_transaction(basic_info, trace):
        return False

    # No total supply
    elif not total_supply:
        return False

    else:
        largest_range = find_largest_number(total_supply_dict)
        possible_hack = (largest_range >= 0.1)
        return possible_hack
