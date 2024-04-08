import os
import argparse
from utils.collect_basic_info import collectinfo
from utils.get_events import collect_event
from utils.get_traces import collect_trace
from utils.decode_event import decode_event_json
from utils.decode_trace import decode_trace_json
from utils.other_balance import collect_token
from utils.eth_balance import collect_eth


def main(input_file):
	# Create result directory if it doesn't exist
	os.makedirs('result', exist_ok=True)

	# Read raw data from file
	raw_file = []
	with open(input_file, 'r') as file:
		# Read each line of the file
		for line in file:
			raw_file.append(line.rstrip('\n'))

	# Collect basic information
	basic_info = collectinfo(raw_file)
	basic_info.to_csv('result/basic_info.csv')

	# Collect events
	collect_event(raw_file)

	# Collect traces
	collect_trace(raw_file)

	# Decode event JSON
	decode_event_json()

	# Decode trace JSON
	decode_trace_json()

	# Collect token balances
	collect_token()
	# Collect ETH balances
	collect_eth()

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("input_file", help="Path to the input file")
	args = parser.parse_args()
	main(args.input_file)