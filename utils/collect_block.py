import os
import json
import subprocess

cast_bin = os.environ.get("CAST_BIN", "cast")

# collect block using foundry cast
def cast_block_run(block_number, rpc_url):
    # define the command
    command = [
        "cast", "block", str(block_number),
        "--rpc-url", rpc_url, "--json"
    ]

    # run the command and capture the output
    block_result = subprocess.run(command, capture_output=True, text=True, check=True)

    # load block related data
    text_output = block_result.stdout.strip()
    block_data = json.loads(text_output)

    return block_data

# collect all transactions' envInfo and stats from one block
def collect_block_all(block_number, endpoint):
    # get all transactions from the block
    block_tx_list = cast_block_run(block_number, endpoint).get("transactions", [])
    return block_tx_list