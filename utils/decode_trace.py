import requests
import json
from os import listdir
from eth_abi import decode
import base64
import os
from lookup_function import get_function_signature

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

# Function to decode trace JSON files
def decode_trace_json(folder_prefix="result"):
    json_file_path = folder_prefix + '/decoded_trace/'
    os.makedirs(json_file_path, exist_ok=True)

    # Get list of JSON files in trace_json directory
    jsonlist = listdir(folder_prefix + '/trace_json')
    for i in jsonlist:
        file = open(folder_prefix + '/trace_json/' + i)
        traces = []
        tx = json.load(file)
        for trace in tx:
            new_trace = {}
            new_trace["type"] = trace['type']
            if 'error' in trace.keys():
                new_trace["type"] = 'error'
                new_trace["subtype"] = trace['error']
            if trace["result"]:
                new_trace["gasUsed"] = int(trace["result"]["gasUsed"][2:], 16)
            new_trace["subtraces"] = trace["subtraces"]
            new_trace["traceAddress"] = trace["traceAddress"]
            if trace['type'] == 'create':
                new_trace["address"] = trace["result"]["address"]
            elif trace['type'] == 'suicide':
                new_trace["address"] = trace["action"]["address"]
                new_trace["balance"] = int(trace["action"]["balance"][2:], 16)
                new_trace["refundAddress"] = trace["action"]["refundAddress"]
            if trace['type'] == 'call':
                new_trace["from"] = trace["action"]["from"]
                new_trace["to"] = trace["action"]["to"]
                new_trace["value"] = int(trace["action"]["value"][2:], 16)
                if len(trace["action"]['input']) == 2:
                    new_trace["type"] = 'fallback'
                else:
                    func_hash = trace["action"]['input'][2:10]
                    input_hash = trace["action"]['input'][10:]
                    func_name = get_function_signature(func_hash)

                    if func_name:
                        new_trace["function"] = func_name
                        new_trace["input"] = decode_input(func_name, input_hash)
                    else:
                        new_trace["function"] = func_hash
                        new_trace["input"] = decode_input(func_hash, input_hash)
            traces.append(new_trace)
        with open(json_file_path + i, 'w') as jsonfile:
            json.dump(traces, jsonfile, default=convert_bytes_to_string, indent=2)
        print('decode_trace_finished', i)
