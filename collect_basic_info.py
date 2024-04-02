import pandas as pd
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
def collectinfo(raw_list):
	new_dataframe_columns = ['hash', 'value', 'from', 'to', 'gasUsed']
	new_dataframe = pd.DataFrame(columns=new_dataframe_columns)
	for transaction_hash in raw_list:
		transaction = w3.eth.get_transaction(transaction_hash)
		receipt = w3.eth.get_transaction_receipt(transaction_hash)
		sender = transaction['from'].lower()
		recipient = transaction['to'].lower()
		transaction_data = {
			'hash': transaction_hash,
			'value': transaction['value'] / 1e18,
			'from': sender,
			'to': recipient,
			'gasUsed': receipt['gasUsed'],
		}
		new_dataframe.loc[len(new_dataframe)] = transaction_data
	return new_dataframe