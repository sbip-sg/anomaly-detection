import pandas as pd
from web3 import Web3

# Initialize Web3 instance with the RPC provider
w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))


# Function to collect transaction information and return as a DataFrame
def collectinfo(raw_list):
	# Define columns for the new DataFrame
	new_dataframe_columns = ['hash', 'value', 'from', 'to', 'gasUsed']
	# Create an empty DataFrame with defined columns
	new_dataframe = pd.DataFrame(columns=new_dataframe_columns)

	# Loop through each transaction hash in the input list
	for transaction_hash in raw_list:
		# Get transaction details
		transaction = w3.eth.get_transaction(transaction_hash)
		# Get transaction receipt
		receipt = w3.eth.get_transaction_receipt(transaction_hash)

		# Extract sender and recipient addresses, converting to lowercase for consistency
		sender = transaction['from'].lower()
		recipient = transaction['to'].lower()

		# Construct dictionary containing transaction data
		transaction_data = {
			'hash': transaction_hash,
			'value': transaction['value'] / 1e18,  # Convert value from Wei to Ether
			'from': sender,
			'to': recipient,
			'gasUsed': receipt['gasUsed'],  # Get gas used from transaction receipt
		}

		# Append transaction data to the DataFrame
		new_dataframe.loc[len(new_dataframe)] = transaction_data

	# Return the DataFrame containing transaction information
	return new_dataframe