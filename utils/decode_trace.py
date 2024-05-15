import json
from os import listdir
from eth_abi import decode
import base64
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

# Function to split parameters in a string
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

# Function to decode input data based on function signature
def decode_input(event_text, input_hash):
    input_list = []
    if len(input_hash) % 64 == 0:
        if len(event_text.split('(', 1)) != 1 and len(input_hash) != 0 and len(event_text.split(';')) == 1:
            start_index = event_text.find('(')
            end_index = event_text.rfind(')')
            raw_parameters = event_text[start_index + 1:end_index]
            if len(raw_parameters) != 0:
                parameters = split_parameters(raw_parameters)
                values = decode(parameters, bytes.fromhex(input_hash))
                for value in values:
                    if isinstance(value, bytes):
                        transformed_value = value.hex()
                        input_list.append(transformed_value)
                    else:
                        input_list.append(value)
        elif len(input_hash) != 0:
            chunks = [input_hash[i:i + 64] for i in range(0, len(input_hash), 64)]
            for line in chunks:
                count_of_zeros = len(line) - len(line.lstrip('0'))
                if count_of_zeros >= 24 and count_of_zeros < 30:
                    input_list.append(decode(['address'], bytes.fromhex(line))[0])
                elif count_of_zeros >= 30 and count_of_zeros < 60:
                    input_list.append(decode(['uint256'], bytes.fromhex(line))[0])
    return input_list

# Function to convert bytes to base64 encoded string
def convert_bytes_to_string(obj):
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode('utf-8')
    raise TypeError("Object of type {} not serializable".format(type(obj)))

def decode_input_events(chunks, data = False):
    input_list = []
    if data:
        raw = chunks[2:]
        chunks = ['0x'+ raw[i:i + 64] for i in range(0, len(raw), 64)]
    for line in chunks:
        line = line[2:]  # Remove '0x' prefix
        count_of_zeros = len(line) - len(line.lstrip('0'))  # Count leading zeros
        if count_of_zeros >= 24 and count_of_zeros < 30:  # Address type
            input_list.append(decode(['address'], bytes.fromhex(line))[0])
        elif count_of_zeros >= 30 and count_of_zeros < 64:  # uint256 type
            input_list.append(decode(['uint256'], bytes.fromhex(line))[0])
    return input_list

# Function to decode trace JSON files
def decode_trace_json(folder_prefix="result"):
    json_file_path = folder_prefix + '/decoded_trace/'
    os.makedirs(json_file_path, exist_ok=True)

    # Get list of JSON files in trace_json directory
    jsonlist = listdir(folder_prefix + '/invocation_tree')
    for i in jsonlist:
        file = open(folder_prefix + '/invocation_tree/' + i)
        invocation_tree = []
        tx = json.load(file)
        for trace in tx:
            new_trace = {}
            new_trace["type"] = trace['kind'].lower()
            if 'gas_used' in trace.keys():
                new_trace["gasUsed"] = trace["gas_used"]
            if 'value' in trace.keys():
                new_trace["value"] = int(trace["value"][2:], 16)
            # if trace['type'] == 'create':
            # new_trace["address"] = trace["result"]["address"]
            # if trace['type'] == 'suicide':
            #   new_trace["address"] = trace["action"]["address"]
            #   new_trace["balance"] = int(trace["action"]["balance"][2:], 16)
            #   new_trace["refundAddress"] = trace["action"]["refundAddress"]
            if trace['kind'].lower() == 'call' or trace['kind'].lower() == 'delegatecall' or trace[
                'kind'].lower() == 'staticcall':
                new_trace["from"] = trace["from"]
                new_trace["to"] = trace["to"]
                if trace['decoded']['func']:
                    new_trace["function"] = trace['decoded']['func']['signature']
                    new_trace["input"] = decode_input(new_trace["function"], trace['data'][8:])
                else:
                    func_hash = trace['data'][:8]
                    input_hash = trace['data'][8:]
                    func_name = get_function_signature(func_hash)

                    if func_name:
                        new_trace["function"] = func_name
                        new_trace["input"] = decode_input(func_name, input_hash)
                    else:
                        new_trace["function"] = func_hash
                        new_trace["input"] = decode_input(func_hash, input_hash)

            if trace['kind'].lower() == 'event':
                new_trace["address"] = trace["from"]
                if trace['decoded']:
                    new_trace["function"] = trace['decoded']['name']
                elif len(trace['raw']['topics']) != 0:
                    func_hash = trace['raw']['topics'][0][2:]
                    event_name = get_event_db_signature(func_hash)
                    if event_name:
                        new_trace["function"] = event_name
                    else:
                        new_trace["function"] = func_hash
                new_trace["input"] = decode_input_events(trace['raw']['topics'][1:])
                new_trace['data'] = decode_input_events(trace['raw']['data'], data=True)
            invocation_tree.append(new_trace)
                
        with open(json_file_path + 'decode_' + i, 'w') as jsonfile:
            json.dump(invocation_tree, jsonfile, default=convert_bytes_to_string, indent=2)
        print('decode_invocation_tree_finished', i)
