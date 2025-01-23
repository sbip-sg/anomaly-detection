import json
from os import listdir
from eth_abi import decode
import os
import re

try:
    from .db_tools import get_function_signature, get_event_db_signature
except ImportError:
    from db_tools import get_function_signature, get_event_db_signature

# Parse the structure of parameter types of a function
def parse_structure(structure):
    def parse_element(element):
        # Match a single element type (letters and numbers)
        match_single = re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', element)
        if match_single:
            return {"type": element}

        # Match a list type (e.g., 'type[]' or 'type[n]')
        match_list = re.fullmatch(r'(.*)\[(\d*)\]', element)
        if match_list:
            inner_type = parse_element(match_list.group(1).strip())  # Recursively parse the inner type
            size = match_list.group(2)  # Size, '' for infinite lists
            return {
                "type": "list",
                "inner_type": inner_type,
                "size": int(size) if size.isdigit() else "infinite"
            }

        # Match a structure (e.g., '(type1,type2)')
        if element.startswith('(') and element.endswith(')'):
            inner_types = split_structure(element[1:-1])
            return {
                "type": "structure",
                "elements": [parse_element(t) for t in inner_types]
            }

        raise ValueError(f"Unknown element: {element}")

    def split_structure(struct):
        # Splits a structure string by ',' considering nested structures and lists
        result = []
        depth = 0
        current = []
        for char in struct:
            if char == ',' and depth == 0:
                result.append(''.join(current).strip())
                current = []
            else:
                if char == '(' or char == '[':
                    depth += 1
                elif char == ')' or char == ']':
                    depth -= 1
                current.append(char)
        if current:
            result.append(''.join(current).strip())
        return result

    # Start parsing
    return parse_element(structure)

def process_function(function):
    # Can not determine the function of this hash
    if function.find(';') != -1:
        return function, {}
    try:
        # Separate function name and parameters
        index = function.find('(')
        function_name = function[:index]
        parameters = parse_structure(function[index:])
        return function_name, parameters

    # The function is not simple function(parameters)
    except:
        return function, {}

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
                    print(f"Error: {function_text} input hash can not be decoded")
                    input_list = decode_unknown_input(input_hash, data=True, event=False)
        # Otherwise, we use above function to guess the input 64 digits.
        elif len(input_hash) != 0:
            input_list = decode_unknown_input(input_hash, data=True, event=False)
    return input_list


# Function to convert bytes to base64 encoded string
def convert_bytes_to_string(obj):
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError("Object of type {} not serializable".format(type(obj)))


# When we do not know parameter types, we manually separate inputs.
def decode_unknown_input(chunks, data=False, event=True):
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
        chunks = ['0x' + raw[i:i + 64] for i in range(0, len(raw), 64)]
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


def parse_grouped_elements(input_str):
    # Step 1: Handle the special cases
    if '\"' in input_str:
        return [input_str]
    if 'ecrecover:' in input_str.lower():
        input_str = re.findall(r'\[(.*?)\]', input_str)[0]
    # Replace ', ' with ','
    input_str = input_str.replace(', ', ',')
    # Replace patterns like 'number [number e number]' or 'number [number.number e number]' with just 'number'
    input_str = re.sub(r'(\d+)\s*\[\d+(\.\d+)?e\d+\]', r'\1', input_str)

    # Replace patterns like '-number [-number e number]' or '-number [-number.number e number]' with just '-number'
    input_str = re.sub(r'(-\d+)\s*\[-\d+(\.\d+)?e\d+\]', r'\1', input_str)
    # input lower
    input_str = input_str.lower()

    def parse_recursive(s, index):
        result = []
        current = []

        while index < len(s):
            char = s[index]
            if char == ',':
                # Add current element to result if not empty
                if current:
                    result.append(''.join(current).strip())
                    current = []
            elif char in '[(':
                # Start a new group, call recursively
                group, index = parse_recursive(s, index + 1)
                result.append(group)
            elif char in '])':
                # End of current group, finalize and return
                if current:
                    result.append(''.join(current).strip())
                return result, index
            else:
                # Part of an element
                current.append(char)
            index += 1

        # Finalize last element if outside any group
        if current:
            result.append(''.join(current).strip())
        return result, index
    # Step 2: Parse the remaining string
    parsed_list, _ = parse_recursive(input_str, 0)
    return parsed_list

# guess the type of a parameter
def guess_type(parameter):
    def is_lowercase_address(address):
        """
        Checks whether the given string is a valid lowercase Ethereum address.

        Args:
            address (str): The string to check.

        Returns:
            bool: True if the string is a valid lowercase Ethereum address, False otherwise.
        """
        if not isinstance(address, str):
            return False
        # Ethereum addresses should be 42 characters long and start with '0x'
        if len(address) != 42 or not address.startswith("0x"):
            return False
        # Check if the remaining 40 characters are lowercase hexadecimal
        return bool(re.fullmatch(r"0x[0-9a-f]{40}", address))

    def is_bool(bool_string):
        return bool_string in ['true', 'false']
    while isinstance(parameter, list):
        parameter = parameter[0]
    if isinstance(parameter, int):
        return 'int'
    if is_bool(parameter):
        return 'bool'
    elif parameter.isdigit():
        return 'int'
    elif is_lowercase_address(parameter):
        return 'address'
    elif parameter.startswith('0x'):
        return 'bytes'
    else:
        return 'string'

# check whether elements in a list have the same type
def check_list(plist, ptype):
    if len(plist) == 0:
        return True
    for element in plist[0]:
        if guess_type(element) not in ptype:
            return False
    return True

# Add the inputs into parameters
def input_parameter(inputs, parameters, inner = False):
    if 'elements' in parameters:
        elements = parameters['elements']
        if len(elements) == len(inputs):
            for key in range(len(inputs)):
                if elements[key]['type'] not in ['list', 'structure']:
                    if not inner:
                        value = inputs[key][0]
                    else:
                        value = inputs[key]
                    if guess_type(value) in elements[key]['type']:
                        elements[key]['value'] = value
                elif elements[key]['type'] == 'list':
                    if elements[key]['inner_type']['type'] not in ['list', 'structure']:
                        if check_list(inputs[key], elements[key]['inner_type']['type']):
                            elements[key]['value'] = inputs[key]
                    else:
                        elements[key]['value'] = inputs[key]
                elif elements[key]['type'] == 'structure':
                    elements[key] = input_parameter(inputs[key][0], elements[key], True)
    return parameters

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
            if 'call' in trace['kind'].lower():
                new_trace["from"] = trace["from"]
                new_trace["to"] = trace["to"]
                new_trace["depth"] = trace["depth"]
                new_trace['parent']= trace['parent']
                new_trace['children']= trace['children']
                new_trace["call_idx"] = trace['call_idx']

                # Move state changes into new trace
                if 'statechanges' in trace.keys():
                    new_trace["statechanges"] = trace['statechanges']

                # When foundry can decode it.
                func_hash = trace['data'][2:10]
                input_hash = trace['data'][10:]
                new_trace["selector"] = func_hash
                if trace['decoded']['call_data']:
                    new_trace["decodeStatue"] = "foundry"
                    new_trace["function"] = trace['decoded']['call_data']['signature']
                    new_trace["functionName"], new_trace["parameters"] = process_function(new_trace["function"])
                    new_args = []
                    args = trace['decoded']['call_data']['args']
                    for arg in args:
                        arg = parse_grouped_elements(arg)
                        new_args.append(arg)
                    new_trace["input"] = new_args
                    if len(new_args) == 0 and len(trace['data'][10:]) != 0:
                        new_trace["input"] = decode_input(new_trace["function"], input_hash)
                        new_trace["decodeStatue"] = "database"
                    else:
                        new_trace['parameters'] = input_parameter(new_trace['input'], new_trace['parameters'])

                else:

                    # Use function signature database to search for 4bytes
                    func_name = get_function_signature(func_hash)

                    if func_name:
                        new_trace["decodeStatue"] = "database"
                        new_trace["function"] = func_name
                        new_trace["functionName"], new_trace["parameters"] = process_function(new_trace["function"])
                        new_trace["input"] = decode_input(func_name, input_hash)
                    else:
                        # If we can not get the function name, just use function hash as name
                        new_trace["decodeStatue"] = "none"
                        new_trace["function"] = func_hash
                        new_trace["functionName"], new_trace["parameters"] = func_hash, {}
                        new_trace["input"] = decode_input(func_hash, input_hash)
                new_trace["output"] = decode_input(func_hash, trace['output'][2:])

            # If trace is an event log
            elif trace['kind'].lower() == 'event':
                new_trace["address"] = trace["from"]
                new_trace['parent'] = trace['parent']
                new_trace["depth"] = trace["depth"] + 1

                # When foundry can decode it.
                if trace['decoded']['name']:
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

            # If trace is a create log
            elif 'create' in trace['kind'].lower():

                new_trace["from"] = trace["from"]
                new_trace["to"] = trace["to"]
                new_trace["depth"] = trace["depth"]
                new_trace['data'] = trace['data']
            elif trace['kind'].lower() == 'selfdestruct':

                new_trace["address"] = trace["address"]
                new_trace["refund_target"] = trace["refund_target"]
                new_trace["depth"] = trace["depth"]

            # according to the depth of trace, find its location
            if new_trace['depth'] + 1 >= len(locations):
                while len(locations) <= new_trace['depth']:
                    locations.append(-1)
            locations[new_trace["depth"]] += 1
            for position in range(new_trace["depth"] + 1, len(locations)):
                locations[position] = -1
            new_trace['location'] = locations[:new_trace["depth"] + 1]

            invocation_tree.append(new_trace)

        # Dump the decoded invocation tree to a json file
        with open(json_file_path + 'decode_' + i, 'w') as jsonfile:
            json.dump(invocation_tree, jsonfile, default=convert_bytes_to_string, indent=2)
        print('decode_invocation_tree_finished', i)
