import json
import pandas as pd
from os import listdir
from web3 import Web3
from utils.get_rate import get_rate

abi_file = open("utils/erc20.abi.json")
abi = json.load(abi_file)

currency_dict = {}
chain_dict = {
	"arbitrum": "ETH",
	"Avalanche": "AVAX",
	"Base": "ETH",
	"bsc": "BNB",
	"eth": "ETH",
	"fantom": "FTM",
	"Fuse Mainnet": "FUSE",
	"gnosis": "XDAI",
	"moonriver": "MOVR",
	"optimism": "ETH",
	"polygon": "MATIC",
	"celo": "CELO"
}

def get_currency(hash, w3):
	if hash not in currency_dict.keys():
		address = Web3.to_checksum_address(hash)
		contract = w3.eth.contract(
			address=address,
			abi=abi,
		)
		currency = contract.functions.symbol().call()
		decimal = contract.functions.decimals().call()
		currency_dict[hash] = (currency, decimal)
	else:
		(currency, decimal) = currency_dict[hash]
	return currency, decimal


def update_summary(summary, address, currency, amount):
	if address not in summary:
		summary[address] = {}
	if currency not in summary[address]:
		summary[address][currency] = 0
	summary[address][currency] += amount
	return summary


# Function to handle other transfer transactions
def othertransfer(summary, currency, from_address, to_address, amount, flow):
	summary = update_summary(summary, from_address, currency, -amount)
	summary = update_summary(summary, to_address, currency, amount)
	if amount != 0:
		flow.loc[len(flow)] = [from_address, to_address, currency, amount]

	return summary


# Function to deal with transfer transactions
def deal_transfer(summary, currency, trace, flow):
	from_address = trace["from"]
	to_address = trace["to"]
	amount = trace["value"]/1e18

	summary = update_summary(summary, from_address, currency, -amount)
	summary = update_summary(summary, to_address, currency, amount)
	if amount != 0:
		flow.loc[len(flow)] = [from_address, to_address, currency, amount]

	return summary

# Function to deal with self-destruct transactions
def deal_selfdestruct(summary, currency, trace, flow):
	from_address = trace["from"]
	to_address = trace["refundAddress"]
	amount = trace["balance"]/1e18

	summary = update_summary(summary, from_address, currency, -amount)
	summary = update_summary(summary, to_address, currency, amount)
	if amount != 0:
		flow.loc[len(flow)] = [from_address, to_address, currency, amount]

	return summary

def find_address_transfer_event(trace, input):
	from_address = input[0]
	if len(input) > 2:
		to_address = input[1]
		amount = input[2]
	elif len(input) == 2 and trace['data']:
		amount = trace['data'][0]
		to_address = input[1]
	elif trace['data']:
		amount = trace['data'][0]
		from_address = '0x' + '0' * 40
		to_address = input[0]
	else:
		amount = 0
		to_address = '0x' + '0' * 40
	return from_address, to_address, amount

def update_memory(trace, memory):
	if trace['type'] == 'call':
		memory['last_call_to'] = trace["to"]
	if trace['type'] == 'call' and 'withdraw' in trace["function"].lower():
		memory['last_withdraw'] = trace["to"]
	return memory

def remove_zeros(total_dict):
	for key1 in total_dict.keys():
		for key2 in total_dict[key1].keys():
			keys_to_delete = [key for key, value in total_dict[key1][key2].items() if value[0] == 0]
			for key3 in keys_to_delete:
				del total_dict[key1][key2][key3]
	for key1 in total_dict.keys():
		keys_to_delete = [key for key, value in total_dict[key1].items() if value == {}]
		for key2 in keys_to_delete:
			del total_dict[key1][key2]
	return total_dict

def address_to_currency(address, w3):
	try:
		currency, decimal = get_currency(address.lower(), w3)
	except Exception as e:
		print('Error: can not get transfer currency', input[0].lower())
		currency, decimal = address, 0
	return currency, decimal

def collect_token(timestamp_dict, chain, rpc, folder_prefix="result"):
	total_dict = {}
	token = chain_dict[chain]
	flow = pd.DataFrame(columns=['from', 'to', 'currency', 'value'])
	jsonlist = listdir(folder_prefix + '/invocation_tree')
	w3 = Web3(Web3.HTTPProvider(rpc))
	for i in jsonlist:
		file = open(folder_prefix + '/invocation_tree/' + i)
		summary_dict = {}
		traces = json.load(file)
		memory ={
		"last_call_to" : '',
		"last_withdraw" : '',
		"out_of_gas" : False
		}
		for trace in traces:
			if not memory['out_of_gas']:
				if trace['type'] == 'event':
					eventname = trace["function"]
					input = trace['input']
					if eventname.lower() == 'transfer':
						currency, decimal = address_to_currency(memory['last_call_to'], w3)
						from_address, to_address, amount =  find_address_transfer_event(trace, input)
						summary_dict = othertransfer(summary_dict, currency, from_address, to_address,
						                             amount / pow(10, decimal), flow)
					elif eventname.lower() == 'withdrawal':
						currency, decimal = address_to_currency(memory['last_withdraw'], w3)
						from_address = input[0]
						amount = trace['data'][0]
						summary_dict = othertransfer(summary_dict, currency, from_address,memory['last_withdraw'],
						                             amount / pow(10, decimal), flow)
					elif eventname.lower() == 'deposit':
						currency, decimal = address_to_currency(memory['last_call_to'], w3)
						to_address = input[0]
						amount = trace['data'][0]
						summary_dict = othertransfer(summary_dict, currency, memory['last_call_to'], to_address,
						                             amount / pow(10, decimal), flow)
				else:
					memory = update_memory(trace, memory)
					if trace['type'] == 'call' or trace['type'] == 'staticcall' and trace["value"] != 0:
						summary_dict = deal_transfer(summary_dict, token, trace, flow)
			if trace['type'] == 'call' and trace['status'] == "OutOfGas":
				memory['out_of_gas'] = not memory['out_of_gas']
		if len(traces) != 0:
			transaction_hash = i.split("_")[2].split(".")[0]
			time_stamp = timestamp_dict[transaction_hash]
			for address in summary_dict.keys():
				address_balance = summary_dict[address]
				for token in address_balance:
					value = address_balance[token]
					rate = get_rate(time_stamp, token)
					address_balance[token] = [value, value * rate]
			total_dict[transaction_hash] = summary_dict
	total_dict = remove_zeros(total_dict)
	with open(folder_prefix + '/balance.json', 'w') as json_file:
		json.dump(total_dict, json_file, indent=2)
	flow.to_json(folder_prefix + '/tokenflow.json', orient='records')
