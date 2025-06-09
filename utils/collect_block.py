from web3 import Web3

# collect all transactions' envInfo and stats from one block
def collect_block_all(block_number, endpoint):
    # get all transactions from the block
    w3 = Web3(Web3.HTTPProvider(endpoint))
    block_tx_list = []
    try:
        block = w3.eth.get_block(int(block_number), full_transactions=False)
        block_tx_list = block['transactions']
    except Exception as e:
        print(f'unable to find transactions in {block_number}:', e)
    return block_tx_list