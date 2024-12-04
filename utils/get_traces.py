# Function to collect transaction traces and save them as JSON files
import json
import os
import subprocess
import copy

cast_bin = os.environ.get('CAST_BIN', 'cast')


def dfs_recursive(tree, node, visited=None, result=None):
    if visited is None:
        visited = set()  # To keep track of visited nodes
    if result is None:
        result = []  # To store the result of visited nodes

    result.append(node)  # Add the current node to the result list
    visited.add(node)

    for child in tree.get(node, []):  # Get the children of the current node
        if child not in visited:
            dfs_recursive(tree, child, visited, result)

    return result  # Return the accumulated result

def find_position_before_nth_int(mixed_list, n):
    int_count = 0  # Counter for integers
    for i in range(len(mixed_list)):
        if isinstance(mixed_list[i], int):
            int_count += 1
            if int_count == n + 1:
                return i  # Return the position before the nth integer
    return len(mixed_list)  # Return -1 if the nth integer does not exist

def insert_event(log_idx, tree_relation, parent, position):
    plist = tree_relation[parent] # Get the parent's children list
    if len(plist) == position: # If the log is the last of the list
        plist.append(log_idx)
    else: # If the log is before some call traces (ignore events)
        e_position = find_position_before_nth_int(plist, position)
        plist.insert(e_position, log_idx)
    return tree_relation


def cast_run(rpc_url, txhash, raw, output):
    print('Foundry Start')
    # Define the command
    command = [
        'cast', 'run', txhash,
        '-r', rpc_url, '--decode-internal', '--with-state-changes', '-j'
    ]

    if 'nus' in rpc_url:
        command.append('--no-rate-limit')

    # Run the command and capture the output
    result = subprocess.run(command, capture_output=True, text=True, check=True)

    lines = result.stdout.strip().split('\n')
    traces_index = -1

    for index, line in enumerate(lines):
        if 'Traces:' in line:
            traces_index = index
            break
    output_lines = lines[traces_index + 1:]

    filtered_output = '\n'.join(output_lines)  # Join the remaining lines
    json_output = json.loads(filtered_output)

    # Write the filtered output to a file
    # with open(raw, 'w') as raw_file:
    #   json.dump(json_output, raw_file, indent = 2)

    formal_result = original_json(json_output['arena'])

    # Write the filtered output to a file
    with open(output, 'w') as json_file:
        json.dump(formal_result, json_file, indent=2)

    # Return the loaded JSON from the filtered output
    print('Foundry End')

    return formal_result


def collect_trace(transaction_hash, edpool, folder_prefix="result"):
    # Create a directory if it doesn't exist

    # store raw result of cast (too large to process now)
    # raw_directory = folder_prefix + '/raw_json'
    # os.makedirs(raw_directory, exist_ok=True)
    output_directory = folder_prefix + '/trace_json'
    os.makedirs(output_directory, exist_ok=True)
    # raw_filename = os.path.join(raw_directory, f"raw_{transaction_hash}.json")
    filename = os.path.join(output_directory, f"trace_{transaction_hash}.json")
    rpc = edpool.endpoint_by_chain()
    while True:
        try:
            # Initialize Web3 instance with the RPC provider
            cast_run(rpc, transaction_hash, 'raw', filename)
            break
        except subprocess.CalledProcessError as e:
            rpc = edpool.mark_endpoint_broken(rpc)
            print(f'Error processing request: {e}\n retry ... ')
            # Handle the CalledProcessError

        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred: {e}")
            # Handle other unexpected exceptions

        print('trace_finished', transaction_hash)


# Used to Transform New Version of Foundry Output to Clear Json
def tree_structure(dict_list):
    # Collect the new calls
    new_element_dict = {}
    new_event_dict = {}
    new_sd_dict = {}
    tree_relation = {}
    log_idx = 0
    sd_idx = 0

    for element in dict_list:
        # Collect basic information and position/relations of a call
        idx = element["idx"]
        parent = element['parent']
        children = element['children']
        copy_children = copy.deepcopy(children)
        depth = element['trace']['depth']
        new_trace = element['trace']

        if element['trace']['kind'].lower() == 'delegatecall':
            # for a delegate call, the address of its events is address of the call triggering it (parent)
            event_address = new_element_dict[parent]['event_address']

        else:

            # for other calls, the address of their events are the same of their addresses.
            event_address = new_trace['address'].lower()

        # If the call has event logs
        if len(element['logs']) != 0:
            # Assume that the sequence of the logs is not reversed
            # Since the events of inner calls generated by this call will be popped first
            # The log stack should be LIFO and the sequence of the logs need to be reversed

            # If a call has event
            for log in element['logs']:
                # The position is where the log is supposed to be in the call's children.
                log_position = log['position']
                new_log = {
                    'from': event_address,
                    'kind': 'event',
                    'decoded': log['decoded'],
                    'raw': log['raw_log'],
                    'depth': depth
                }

                new_event_dict['e' + str(log_idx)] = {'parent': idx, 'position': log_position, 'log_content': new_log}
                log_idx += 1
        statechanges, opcodes = collect_state_changes(new_trace['steps'])
        # Collect the new call
        new_call = {
            'from': new_trace['caller'].lower(),
            'to': new_trace['address'].lower(),
            'depth': depth,
            'kind': new_trace['kind'].lower(),
            'success': new_trace['success'],
            'gas_used': new_trace['gas_used'],
            'value': new_trace['value'],
            'data': new_trace['data'],
            'output': new_trace['output'],
            # Get all state changes in steps
            'statechanges': statechanges,
            'opcodes': opcodes,
            'status': new_trace['status'],
            'decoded': new_trace['decoded'],
            'parent': parent,
            'children': copy_children,
            'call_idx': idx
        }
        if new_trace['selfdestruct_address']:
            new_selfdestruct = {
                'address': new_trace['selfdestruct_address'].lower(),
                'refund_target': new_trace['selfdestruct_refund_target'].lower(),
                'depth': depth + 1,
                'kind': 'selfdestruct',
                'value': new_trace['selfdestruct_transferred_value']
            }
            new_sd_dict['sd' + str(sd_idx)] = new_selfdestruct
            children.append('sd' + str(sd_idx))
            sd_idx += 1

        new_element_dict[idx] = {'parent': parent, 'children': children, 'call_content': new_call,
                                 'event_address': event_address}
        tree_relation[idx] = children

    return new_element_dict, new_event_dict, new_sd_dict, tree_relation

def original_json(dict_list):
    # Get the tree related information
    new_element_dict, new_event_dict, new_sd_dict, tree_relation = tree_structure(dict_list)
    new_element_list = []

    # Insert events in its position
    for ev in new_event_dict:
        tree_relation = insert_event(ev, tree_relation, new_event_dict[ev]['parent'], new_event_dict[ev]['position'])

    # DFS to get the trace list
    dfs_index = dfs_recursive(tree_relation, 0)

    # Retrieve calls and events from the dictionaries
    for idx in dfs_index:
        if isinstance(idx, int):
            new_element = new_element_dict[idx]['call_content']
        elif isinstance(idx, str) and idx.startswith('sd'):
            new_element = new_sd_dict[idx]
        else:
            new_element = new_event_dict[idx]['log_content']
        new_element_list.append(new_element)
    return new_element_list


# Collect all state changes in the steps of a call trace
def collect_state_changes(steps):
    state_changes_list = []
    op_code_list = []
    for step in steps:
        op_code_list.append(hex(step['op'])[2:].upper())
        # If a step hs storage change
        if step['storage_change']:
            state_changes_list.append(step['storage_change'])
    return state_changes_list, op_code_list
