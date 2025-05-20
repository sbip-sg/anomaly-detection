from requests.exceptions import HTTPError
from web3 import Web3

# Function to collect transaction information and return as a DataFrame
def collect_info(transaction_hash, edpool):
    rpc = edpool.endpoint_by_chain()
    while True:
        try:
            # Initialize Web3 instance with the RPC provider
            w3 = Web3(Web3.HTTPProvider(rpc))
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

    input_data = str(transaction['input'][:10])

    if transaction['to']:
        recipient = transaction['to'].lower()
        if input_data == "0x":
            is_eoa = True
        else:
            try:
                checked_recipient = w3.to_checksum_address(recipient)
                code = w3.eth.get_code(checked_recipient)
                is_eoa = code == b''  # True if it's an EOA
            except Exception as e:
                print(f"Failed to check if recipient is EOA: {e}")
                is_eoa = False  # Could not determine
    else:
        recipient = 'empty'
        is_eoa = 'created'

    # Construct dictionary containing transaction data
    transaction_data = {
        'hash': transaction_hash,
        'value': transaction['value'] / 1e18,  # Convert value from Wei to Ether
        'from': sender,
        'to': recipient,
        'gasLimit': transaction['gas'],  # Get gas limit from transaction receipt
        'gasUsed': receipt['gasUsed'],  # Get gas used from transaction receipt
        'timestamp': timestamp,
        'status': receipt["status"],
        '4byteData': input_data,
        'to_is_eoa': is_eoa
    }

    # Return the DataFrame containing transaction information
    return transaction_data
