from requests.exceptions import HTTPError
from web3 import Web3
from web3.middleware import geth_poa_middleware
from utils.find_rpc import endpoint_by_chain, handle_error

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
def collect_info(transaction_hash, chain, endpoint_idx):
	rpc, endpoint_idx, loop = endpoint_by_chain(chain, endpoint_idx, False)
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
			endpoint_idx = handle_error(chain, endpoint_idx)
			rpc, endpoint_idx,loop = endpoint_by_chain(chain, endpoint_idx, loop)
			print(f'Error processing request: {e}\n retry ... ')
			# Handle HTTP errors

		except Exception as e:
			raise RuntimeError(f"An unexpected error occurred: {e}")
			# Handle other unexpected exceptions
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
		'timestamp': timestamp
	}

	# Return the DataFrame containing transaction information
	return transaction_data, timestamp, endpoint_idx
