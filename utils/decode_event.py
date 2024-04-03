import pandas as pd
from web3 import Web3
import requests
import json
import os
from os import listdir
from eth_abi import decode
import base64

hash = pd.read_csv('dictionary/event_dict.csv')
hashdict = hash.set_index('hash')['event'].to_dict()

base_url = "https://api.etherface.io/v1/signatures/hash/all/"


def decode_input(chunks):
	input_list = []
	for line in chunks:
		line = line[2:]
		count_of_zeros = len(line) - len(line.lstrip('0'))
		if count_of_zeros >= 24 and count_of_zeros < 30:
			input_list.append(decode(['address'], bytes.fromhex(line))[0])
		elif count_of_zeros >= 30 and count_of_zeros < 60:
			input_list.append(decode(['uint256'], bytes.fromhex(line))[0])
	return input_list


def convert_bytes_to_string(obj):
	if isinstance(obj, bytes):
		return base64.b64encode(obj).decode('utf-8')
	raise TypeError("Object of type {} not serializable".format(type(obj)))


jsonlist = listdir('result/event_json')


def decode_event_json():
	json_file_path = 'result/decoded_event/'
	os.makedirs(json_file_path, exist_ok=True)
	for i in jsonlist:
		file = open('result/event_json/' + i)
		events = []
		tx = json.load(file)
		for event in tx:
			new_event = {}
			if event['removed'] == True:
				new_event['removed'] = True
			if len(event["topics"]) != 0:
				func_hash = event["topics"][0][2:]
				if func_hash in hashdict.keys():
					new_event["eventname"] = hashdict[func_hash]
					new_event["topics"] = decode_input(event["topics"][1:])
				else:
					api_url = f"{base_url}{func_hash}/1"
					response = requests.get(api_url)
					if response.status_code == 200:
						result = response.json()
						event_text = result['items'][0]['text']
						new_event["eventname"] = event_text
						hashdict[func_hash] = event_text
					else:
						new_event["eventname"] = func_hash
						hashdict[func_hash] = func_hash
			new_event["topics"] = decode_input(event["topics"][1:])
			new_event["data"] = decode_input([event["data"]])
			new_event['address'] = event['address'].lower()

			events.append(new_event)
		with open(json_file_path + i, 'w') as jsonfile:
			json.dump(events, jsonfile, default=convert_bytes_to_string, indent=2)
