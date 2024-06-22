import json
from os import listdir
from eth_abi import decode
import os
try:
    from .lookup_function import get_function_signature
except ImportError:
    from lookup_function import get_function_signature

try:
    from .lookup_event import get_event_db_signature
except ImportError:
    from lookup_event import get_event_db_signature

# Function to check if parentheses are balanced in a string
def are_parentheses_balanced(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}

    for char in s:
        if char in mapping.values():
            stack.append(char)
        elif char in mapping:
            if not stack or stack.pop() != mapping[char]:
                return False

    return not stack

# Function to split parameters in a list
def split_parameters(s):
    s_list = s.split(',')
    i = 0
    while i != len(s_list) - 1:
        if are_parentheses_balanced(s_list[i]):
            i += 1
        else:
            # Merge s_list[i] and s_list[i+1]
            s_list[i] += ',' + s_list[i + 1]
            s_list.pop(i + 1)

    return s_list

# Function to decode input data based on function signature.
def decode_input(function_text, input_hash):
    input_list = []
    # For normal call trace, the input could be divided into 64 digits as a parameter
    # excluding the 8 digits as the function name. If abnormal, we ignore that input.
    if len(input_hash) % 64 == 0:
        # If decoded function name is only one(possible to find several function sharing same 4bytes)
        # and function_text have parameters, we use decode from eth_abi package to decode them
        if len(function_text.split('(', 1)) != 1 and len(input_hash) != 0 and len(function_text.split(';')) == 1:
            start_index = function_text.find('(')
            end_index = function_text.rfind(')')
            raw_parameters = function_text[start_index + 1:end_index]
            if len(raw_parameters) != 0:
                parameters = split_parameters(raw_parameters)
                try:
                    values = decode(parameters, bytes.fromhex(input_hash))
                    for value in values:
                        input_list.append(value)
                except Exception as e:
                    print("Error: input hash can not be decoded")
                    input_list = decode_unknown_input(input_hash, data = True, event = False)
        # Otherwise, we use above function to guess the input 64 digits.
        elif len(input_hash) != 0:
            input_list = decode_unknown_input(input_hash, data = True, event = False)
    return input_list

# Function to convert bytes to base64 encoded string
def convert_bytes_to_string(obj):
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError("Object of type {} not serializable".format(type(obj)))

# When we do not know parameter types, we manually separate inputs.
def decode_unknown_input(chunks, data = False, event = True):
    input_list = []
    # There are 3 situations
    # Decoding event data or trace inputs
    if data:
        # event data starts with 0x
        if event:
            raw = chunks[2:]
        # trace inputs not
        else:
            raw = chunks
        # Add 0x for each line 64 digits chunk because event topics have 0x for each topic
        chunks = ['0x'+ raw[i:i + 64] for i in range(0, len(raw), 64)]
    for line in chunks:
        line = line[2:]  # Remove '0x' for prefix or topics
        count_of_zeros = len(line) - len(line.lstrip('0'))  # Count leading zeros
        # Address: normally length == 40, considering starting with zeros, we have a buffer for 10 zeros.
        # The possibility of missing an address is 1/2^40, which means that is mostly impossible.
        if count_of_zeros >= 24 and count_of_zeros < 35:  # Address type
            input_list.append(decode(['address'], bytes.fromhex(line))[0])
        # Number: We consider that the biggest number is 16^28 more than 10e33 and for normal wei = 1e18
        # Normally most numbers are no bigger than 1e15
        elif count_of_zeros >= 35 and count_of_zeros < 64:  # uint256 type
            input_list.append(decode(['uint256'], bytes.fromhex(line))[0])
        # null address
        elif count_of_zeros == 64:  # Address type
            input_list.append(decode(['address'], bytes.fromhex(line))[0])
    return input_list

#find the deepest trace with same address as event's address
def find_depth(address,last_call , memory):
    temp = 0
    for key in memory.keys():
        if memory[key] == address and key > temp and key <= last_call:
            temp = key
    return temp + 1


# Function to decode trace JSON files
def decode_trace_json(folder_prefix="result"):

    # dumping decoded traces and event to invocation_tree folder
    json_file_path = folder_prefix + '/invocation_tree/'
    os.makedirs(json_file_path, exist_ok=True)

    # Get list of JSON files in trace_json directory with raw traces
    jsonlist = listdir(folder_prefix + '/trace_json')
    for i in jsonlist:
        file = open(folder_prefix + '/trace_json/' + i)
        invocation_tree = []
        tx = json.load(file)
        locations = [-1]
        memory = {}
        for trace in tx:
            new_trace = {}
            # extract all kinds of information
            new_trace["type"] = trace['kind'].lower()
            if 'gas_used' in trace.keys():
                new_trace["gasUsed"] = trace["gas_used"]
            if 'value' in trace.keys():
                new_trace["value"] = int(trace["value"][2:], 16)

            # Check whether this trace is from successful call
            if 'status' in trace.keys():
                new_trace["status"] = trace['status']

            # If trace is a function call
            if trace['kind'].lower() == 'call' or trace['kind'].lower() == 'delegatecall' or trace[
                'kind'].lower() == 'staticcall':
                new_trace["from"] = trace["from"]
                new_trace["to"] = trace["to"]
                new_trace["depth"] = trace["depth"]
                last_call_depth = new_trace["depth"]
                if new_trace['depth'] not in memory.keys():
                    memory[new_trace['depth']] = new_trace["from"]

                # When foundry can decode it.
                if trace['decoded']['func']:
                    new_trace["function"] = trace['decoded']['func']['signature']
                    new_trace["input"] = decode_input(new_trace["function"], trace['data'][8:])
                else:
                    func_hash = trace['data'][:8]
                    input_hash = trace['data'][8:]

                    # Use function signature database to search for 4bytes
                    func_name = get_function_signature(func_hash)

                    if func_name:
                        new_trace["function"] = func_name
                        new_trace["input"] = decode_input(func_name, input_hash)
                    else:
                        # If we can not get the function name, just use function hash as name
                        new_trace["function"] = func_hash
                        new_trace["input"] = decode_input(func_hash, input_hash)

            # If trace is an event log
            elif trace['kind'].lower() == 'event':
                new_trace["address"] = trace["from"]

                new_trace["depth"] = find_depth(new_trace["address"], last_call_depth, memory)


                # When foundry can decode it.
                if trace['decoded']:
                    new_trace["function"] = trace['decoded']['name']

                elif len(trace['raw']['topics']) != 0:
                    func_hash = trace['raw']['topics'][0][2:]

                    # Use event signature database to search for 4bytes
                    event_name = get_event_db_signature(func_hash)
                    if event_name:
                        new_trace["function"] = event_name
                    else:
                        new_trace["function"] = func_hash

                # For events, foundry do not give significant parameters
                new_trace["input"] = decode_unknown_input(trace['raw']['topics'][1:])
                new_trace['data'] = decode_unknown_input(trace['raw']['data'], data=True)
                
            # according to the depth of trace, find its location
            if new_trace['depth'] + 1 >= len(locations):
                while len(locations) <= new_trace['depth']:
                    locations.append(-1)
            locations[new_trace["depth"]] += 1
            for position in range(new_trace["depth"]+1, len(locations)):
                locations[position] = -1
            new_trace['location'] = locations[:new_trace["depth"] + 1]

            invocation_tree.append(new_trace)

        # Dump the decoded invocation tree to a json file
        with open(json_file_path + 'decode_' + i, 'w') as jsonfile:
            json.dump(invocation_tree, jsonfile, default=convert_bytes_to_string, indent=2)
        print('decode_invocation_tree_finished', i)
