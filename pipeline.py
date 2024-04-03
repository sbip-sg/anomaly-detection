import os

os.makedirs('result', exist_ok=True)
raw_file = []
with open('file.txt', 'r') as file:
    # Read each line of the file
    for line in file:
        raw_file.append(line.rstrip('\n'))

from utils.collect_basic_info import collectinfo
basic_info = collectinfo(raw_file)
basic_info.to_csv('result/basic_info.csv')

from utils.get_events import collect_event
collect_event(raw_file)

from utils.get_traces import collect_trace
collect_trace(raw_file)

from utils.decode_event import decode_event_json
decode_event_json()

from utils.decode_trace import decode_trace_json
decode_trace_json()

from utils.other_balance import collect_token
collect_token()

from utils.eth_balance import collect_eth
collect_eth()