# Function to collect transaction traces and save them as JSON files
import subprocess
import json
import os

cast_bin = os.environ.get('CAST_BIN', 'cast')


def cast_run(rpc_url, txhash, raw, output):
    print('Foundry Start')
    # Define the command
    command = [
        'cast', 'run', txhash,
        '-r', rpc_url,
        '-q', '--decode-internal', '--with-state-changes', '-j'
    ]

    # Run the command and capture the output
    result = subprocess.run(command, capture_output=True, text=True, check=True)

    lines = result.stdout.strip().split('\n')
    traces_index = -1

    for index, line in enumerate(lines):
        if 'Traces:' in line:
            traces_index = index
            break
    output_lines = lines[traces_index+1:]
    
    filtered_output = '\n'.join(output_lines)  # Join the remaining lines
    json_output = json.loads(filtered_output)

    # Write the filtered output to a file
    #with open(raw, 'w') as raw_file:
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
        raw_directory = folder_prefix + '/raw_json'
        # os.makedirs(raw_directory, exist_ok=True)
        output_directory = folder_prefix + '/trace_json'
        os.makedirs(output_directory, exist_ok=True)
        raw_filename = os.path.join(raw_directory, f"raw_{transaction_hash}.json")
        filename = os.path.join(output_directory, f"trace_{transaction_hash}.json")
        rpc = edpool.endpoint_by_chain()
        while True:
                try:
                        # Initialize Web3 instance with the RPC provider
                        cast_run(rpc, transaction_hash, raw_filename, filename)
                        break
                except subprocess.CalledProcessError as e:
                        rpc = edpool.mark_endpoint_broken(rpc)
                        print(f'Error processing request: {e}\n retry ... ')
                        # Handle the CalledProcessError

                except Exception as e:
                        raise RuntimeError(f"An unexpected error occurred: {e}")
                        # Handle other unexpected exceptions

                print('trace_finished', transaction_hash)


def original_json(dictlist):
    new_element_list = []
    log_list = []
    for element in dictlist:
        address = element['trace']['address'].lower()
        depth = element['trace']['depth']
        if len(element['logs']) != 0:
            for log in element['logs'][::-1]:
                newlog = {
                    'from': address,
                    'kind': 'event',
                    'decoded': log['decoded'],
                    'raw': log['raw_log'],
                    'depth': depth
                }
                log_list.append(newlog)

        rlog_list = log_list[::-1]

        for rlog in rlog_list:
            if depth < rlog['depth']:
                new_element_list.append(rlog)
                rlog_list.remove(rlog)

        log_list = rlog_list[::-1]
        new_trace = element['trace']
        new_call = {
            'from': new_trace['caller'].lower(),
            'to': address,
            'depth': depth,
            'kind': new_trace['kind'].lower(),
            'success': new_trace['success'],
            'gas_used': new_trace['gas_used'],
            'value': new_trace['value'],
            'data': new_trace['data'],
            'output': new_trace['output'],
            'statechanges': collect_state_changes(new_trace['steps']),
            'status': new_trace['status'],
            'decoded': new_trace['decoded'],
        }
        new_element_list.append(new_call)
    rlog_list = log_list[::-1]
    for log in rlog_list:
        new_element_list.append(log)
    return new_element_list

def collect_state_changes(steps):
    state_changes_list = []
    for step in steps:
        if step['storage_change']:
            state_changes_list.append(step['storage_change'])
    return state_changes_list