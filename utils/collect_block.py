import os
import json
import subprocess
from requests.exceptions import HTTPError

cast_bin = os.environ.get("CAST_BIN", "cast")

# collect block using foundry cast
def cast_block_run(block_number, edpool):
    rpc_url = edpool.endpoint_by_chain()
    while True:
        try:
            # define the command
            command = [
                "cast", "block", str(block_number),
                "--rpc-url", rpc_url, "--json"
            ]

            # run the command and capture the output
            block_result = subprocess.run(command, capture_output=True, text=True, check=True)
            break
        except HTTPError as e:
            # Handle HTTP errors
            rpc_url = edpool.mark_endpoint_broken(rpc_url)
            print(f'Error processing request: {e}\n retry ... ')

        except Exception as e:
            # Handle other unexpected exceptions
            raise RuntimeError(f"An unexpected error occurred: {e}")

    # load block related data
    text_output = block_result.stdout.strip()
    block_data = json.loads(text_output)

    return block_data

# collect all transactions' envInfo and stats from one block
def collect_block_all(block_number, endpoint):
    # get all transactions from the block
    block_tx_list = cast_block_run(block_number, endpoint).get("transactions", [])
    return block_tx_list