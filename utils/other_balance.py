import json
import pandas as pd
from os import listdir
from eth_abi import decode
from web3 import Web3
from utils.get_rate import get_rate

w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
abi_file = open("erc20.abi.json")
abi = json.load(abi_file)
# Read event dictionary CSV file and convert it to a dictionary
hash_file = pd.read_csv('dictionary/event_dict.csv')
hashdict = hash_file.set_index('hash')['event'].to_dict()

currencydict = {}
def get_currency(hash):
	if hash not in currencydict.keys():
		address = Web3.to_checksum_address(hash)
		contract = w3.eth.contract(
			address=address,
			abi=abi,
		)
		currency = contract.functions.symbol().call()
		decimal = contract.functions.decimals().call()
		currencydict[hash] = (currency, decimal)
	else:
		(currency, decimal) = currencydict[hash]
	return currency, decimal


# Function to decode input data based on event text and input hash
def decode_input(event_text, input_hash):
	input_list = []
	if len(input_hash) % 64 == 0:
		if len(event_text.split('(', 1)) != 1 and len(input_hash) != 0 and len(event_text.split(';')) == 1:
			start_index = event_text.find('(')
			end_index = event_text.rfind(')')
			raw_parameters = event_text[start_index + 1:end_index]
			if len(raw_parameters) != 0:
				parameters = split_parameters(raw_parameters)
				chunks = [input_hash[i:i + 64] for i in range(0, len(input_hash), 64)]
				if len(parameters) == len(chunks):
					values = decode(parameters, bytes.fromhex(input_hash))
					for value in values:
						input_list.append(value)
		elif len(input_hash) != 0:
			chunks = [input_hash[i:i + 64] for i in range(0, len(input_hash), 64)]
			for line in chunks:
				count_of_zeros = len(line) - len(line.lstrip('0'))
				if 24 <= count_of_zeros < 30:
					input_list.append(decode(['address'], bytes.fromhex(line))[0])
				elif 30 <= count_of_zeros < 60:
					input_list.append(decode(['uint256'], bytes.fromhex(line))[0])
	start_index = event_text.find('(')
	end_index = event_text.rfind(')')
	raw_parameters = event_text[start_index + 1:end_index]
	if len(raw_parameters) != 0 and len(input_list) == 0:
		chunks = [input_hash[i:i + 64] for i in range(0, len(input_hash), 64)]
		for line in chunks:
			count_of_zeros = len(line) - len(line.lstrip('0'))
			if 24 <= count_of_zeros < 30:
				input_list.append(decode(['address'], bytes.fromhex(line))[0])
			elif 30 <= count_of_zeros < 60:
				input_list.append(decode(['uint256'], bytes.fromhex(line))[0])
	return input_list


# Function to check if parentheses are balanced in a string
def are_parentheses_balanced(s):
	stack = []
	mapping = {')': '(', '}': '{', ']': '['}

	for char in s:
		if char in mapping.values():
			stack.append(char)
		elif char in mapping:
			if not stack or stack.pop() != mapping[char]:
				return False

	return not stack


# Function to split parameters in a string
def split_parameters(s):
	s_list = s.split(',')
	i = 0
	while i != len(s_list) - 1:
		if are_parentheses_balanced(s_list[i]):
			i += 1
		else:
			# Merge s_list[i] and s_list[i+1]
			s_list[i] += ',' + s_list[i + 1]
			s_list.pop(i + 1)

	return s_list


# Function to modify the summary of balance of an address
def update_summary(summary, address, currency, amount):
	if address not in summary:
		summary[address] = {}
	if currency not in summary[address]:
		summary[address][currency] = 0

	summary[address][currency] += amount
	return summary


# Function to handle other transfer transactions (not ETH)
def othertransfer(summary, currency, from_address, to_address, amount, flow):
	summary = update_summary(summary, from_address, currency, -amount)
	summary = update_summary(summary, to_address, currency, amount)
	flow.loc[len(flow)] = [from_address, to_address, currency, amount]

	return summary



# Function to collect token transaction details
def collect_token(timestamp_dict, folder_prefix="result"):
	# Initialize dictionary to store total summaries
	total_dict = {}
	flow = pd.DataFrame(columns=['from', 'to', 'currency', 'value'])


	# Get list of JSON files in event_json directory
	jsonlist = listdir(folder_prefix + '/event_json')
	for i in jsonlist:
		file = open(folder_prefix + '/event_json/' + i)
		summary_dict = {}
		tx = json.load(file)
		for log in tx:
			# Determine event name
			if log['topics'][0][2:] in hashdict.keys():
				eventname = hashdict[log['topics'][0][2:]]
			else:
				eventname = log['topics'][0][2:7]

			# Process different types of events
			if len(eventname.split('(')) != 1:
				if eventname.split('(')[0].lower() == 'transfer':
					try:
						currency, decimal = get_currency(log["address"].lower())
					except Exception as e:
						print(e)
						currency, decimal = log["address"].lower(), 1
					from_address = decode(['address'], bytes.fromhex(log['topics'][1][2:]))[0]
					to_address = decode(['address'], bytes.fromhex(log['topics'][2][2:]))[0]
					if len(log['topics'][1:]) == 3:
						amount = decode(['uint256'], bytes.fromhex(log['topics'][3][2:]))[0]
					else:
						amount = decode(['uint256'], bytes.fromhex(log['data'][2:]))[0]
					summary_dict = othertransfer(summary_dict, currency, from_address, to_address, amount/pow(10,decimal), flow)
				if eventname.split('(')[0].lower() == 'withdrawal' and log[
					"address"].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
					currency, decimal = get_currency(log["address"].lower())
					from_address = decode(['address'], bytes.fromhex(log['topics'][1][2:]))[0]
					amount = decode_input(eventname, log['data'][2:])[0]
					summary_dict = othertransfer(summary_dict, currency, from_address, currency, amount/pow(10,decimal),flow)
				if eventname.split('(')[0].lower() == 'deposit' and log[
					"address"].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
					currency, decimal = get_currency(log["address"].lower())
					to_address = decode(['address'], bytes.fromhex(log['topics'][1][2:]))[0]
					amount = decode_input(eventname, log['data'][2:])[0]
					summary_dict = othertransfer(summary_dict, currency, currency, to_address, amount/pow(10,decimal), flow)
		# Store summary dictionary for each transaction
		if len(tx) > 0:
			time_stamp = timestamp_dict[tx[0]["transactionHash"]]
			for address in summary_dict.keys():
				address_balance = summary_dict[address]
				for token in address_balance:
					value = address_balance[token]
					rate = get_rate(time_stamp, token)
					address_balance[token] = [value, value*rate]
			total_dict[tx[0]["transactionHash"]] = summary_dict

	# Write total summaries to a JSON file
	return total_dict, flow
