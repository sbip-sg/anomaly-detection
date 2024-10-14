# Function to collect transaction traces and save them as JSON files
import subprocess
import json
import os

cast_bin = os.environ.get('CAST_BIN', 'cast')


def cast_run(rpc_url, txhash, output):
    print('Foundry Start')
    # Define the command
    command = [
        'cast', 'run', txhash,
        '-r', rpc_url,
        '-q', '--decode-internal', '--with-state-changes', '-j'
    ]

    # Run the command and capture the output
    result = subprocess.run(command, capture_output=True, text=True, check=True)

    # Skip the first line of the output
    output_lines = result.stdout.strip().split('\n')[1:]  # Skip the first line
    filtered_output = '\n'.join(output_lines)  # Join the remaining lines
    json_output = json.loads(filtered_output)

    # Write the filtered output to a file
    with open(output, 'w') as json_file:
        json.dump(json_output, json_file, indent = 2)

    # Return the loaded JSON from the filtered output
    print('Foundry Start')

    return json_output

def collect_trace(transaction_hash, edpool, folder_prefix="result"):
        # Create a directory if it doesn't exist
        output_directory = folder_prefix + '/trace_json'
        os.makedirs(output_directory, exist_ok=True)
        filename = os.path.join(output_directory, f"trace_{transaction_hash}.json")
        rpc = edpool.endpoint_by_chain()
        while True:
                try:
                        # Initialize Web3 instance with the RPC provider
                        cast_run(rpc, transaction_hash, filename)
                        break
                except subprocess.CalledProcessError as e:
                        rpc = edpool.mark_endpoint_broken(rpc)
                        print(f'Error processing request: {e}\n retry ... ')
                        # Handle the CalledProcessError

                except Exception as e:
                        raise RuntimeError(f"An unexpected error occurred: {e}")
                        # Handle other unexpected exceptions

                print('trace_finished', transaction_hash)
