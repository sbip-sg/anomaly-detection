#  python scripts/rule-flashbot-realtime.py --web3-provider-url $ETH_RPC_ENDPOINT flashloan.realtime.txt
from detect_utils.tools import collect_from_file, filter_transaction, check_balance

def has_flashloan(tx_hash, chain):

    trace = collect_from_file(tx_hash, chain, '/invocation_tree/decode_trace_' + tx_hash + '.json')

    for call in trace:
        if call['type'] == 'event':
            pass # ignore event in this detectorF
        elif 'call' in call['type']:
            function_name = call['function']
            if function_name.split('(')[0].lower() == 'flashloan':
                print(f'Flashloan detected in {tx_hash}')
                return True
        else:
            print(f"Unknown trace type: {call['type']}")

    return False
        
def detect_flashloan_transaction(tx_hash, chain):
    basic_info = collect_from_file(tx_hash, chain, '/basic_info.json')
    if not filter_transaction(basic_info):
        return False

    elif not has_flashloan(tx_hash, chain):
        return False

    else:
        possible_hack = True

        return possible_hack