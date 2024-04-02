from collect_basic_info import collectinfo
from get_events import collect_event
from get_traces import collect_trace
from other_balance import collect_token
from eth_balance import collect_eth
from decode_trace import decode_trace_json
from decode_event import decode_event_json

raw_file = []
with open('file.txt', 'r') as file:
    # Read each line of the file
    for line in file:
        raw_file.append(line.rstrip('\n'))

basic_info = collectinfo(raw_file)
basic_info.to_csv('basic_info.csv')

collect_event(raw_file)
collect_trace(raw_file)
collect_token()
collect_eth()
decode_event_json()
decode_trace_json()