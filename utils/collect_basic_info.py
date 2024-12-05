from requests.exceptions import HTTPError
from web3 import Web3
from web3.middleware import geth_poa_middleware


# Function to recursively convert bytes to hexadecimal, lists, and dictionaries
def convert(obj):
    if isinstance(obj, bytes):
        return obj.hex()
    elif isinstance(obj, list):
        return [convert(item) for item in obj]
    elif isinstance(obj, dict):
        return {convert(key): convert(value) for key, value in obj.items()}
    else:
        return obj


# Function to collect transaction information and return as a DataFrame
def collect_info(transaction_hash, edpool):
    rpc = edpool.endpoint_by_chain()
    while True:
        try:
            # Initialize Web3 instance with the RPC provider
            w3 = Web3(Web3.HTTPProvider(rpc))
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            # Get transaction details
            transaction = w3.eth.get_transaction(transaction_hash)
            # Get transaction receipt
            receipt = w3.eth.get_transaction_receipt(transaction_hash)
            break

        except HTTPError as e:
            # Handle HTTP errors
            rpc = edpool.mark_endpoint_broken(rpc)
            print(f'Error processing request: {e}\n retry ... ')

        except Exception as e:
            # Handle other unexpected exceptions
            raise RuntimeError(f"An unexpected error occurred: {e}")
    try:
        timestamp = w3.eth.get_block(transaction['blockNumber'])['timestamp']
    except Exception as e:
        print(e)
        raise ValueError("Can not find timestamp because the block is not recorded.")

    # Extract sender and recipient addresses, converting to lowercase for consistency
    sender = transaction['from'].lower()
    if transaction['to']:
        recipient = transaction['to'].lower()
    else:
        recipient = 'empty'

    # Construct dictionary containing transaction data
    transaction_data = {
        'hash': transaction_hash,
        'value': transaction['value'] / 1e18,  # Convert value from Wei to Ether
        'from': sender,
        'to': recipient,
        'gasUsed': receipt['gasUsed'],  # Get gas used from transaction receipt
        'timestamp': timestamp,
        'blocknumber': transaction['blockNumber']
    }

    # Return the DataFrame containing transaction information
    return transaction_data
