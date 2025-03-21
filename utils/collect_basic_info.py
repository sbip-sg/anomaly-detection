from requests.exceptions import HTTPError
from web3 import Web3
from web3.middleware import geth_poa_middleware

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

    input_data = str(transaction['input'][10:])

    # Construct dictionary containing transaction data
    transaction_data = {
        'hash': transaction_hash,
        'value': transaction['value'] / 1e18,  # Convert value from Wei to Ether
        'from': sender,
        'to': recipient,
        'gasLimit': transaction['gas'],  # Get gas limit from transaction receipt
        'gasUsed': receipt['gasUsed'],  # Get gas used from transaction receipt
        'timestamp': timestamp,
        '4byteData': transaction['input'][:10],
        'zeroCount': input_data.count('0'),
        'oneCount': len(input_data) - input_data.count('0'),
    }

    # Return the DataFrame containing transaction information
    return transaction_data
