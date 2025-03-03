import json
import pandas as pd
from os import listdir
from web3 import Web3
from utils.collect_transfer import find_address_transfer_event, deal_transfer, othertransfer
from utils.collect_currency import get_currency, get_main_token, get_currency_dict
import os

# dict to store token exchange rate
rate_dict = {}


# For the output dict, remove zero values and empty values
def remove_zeros(total_dict):
    # go through all the transactions in the final dict
    for key1 in total_dict.keys():

        # go through all the addresses in the transaction
        for key2 in total_dict[key1].keys():

            # collect zero value items
            keys_to_delete = [key for key, value in total_dict[key1][key2].items() if value[0] == 0]

            # delete zero value items
            for key3 in keys_to_delete:
                del total_dict[key1][key2][key3]

    # go through all the transactions in the final dict
    for key1 in total_dict.keys():

        # collect empty value addresses
        keys_to_delete = [key for key, value in total_dict[key1].items() if value == {}]

        # delete zero value addresses
        for key2 in keys_to_delete:
            del total_dict[key1][key2]
    return total_dict


# collect tokens from decoded invocation tree
def collect_token(transaction_hash, chain, o_from_add, o_to_add, block_number, edpool, folder_prefix):
    # collect balance change of each transaction
    total_dict = {}
    # collect token flows of each transaction
    flow = pd.DataFrame(columns=['from', 'to', 'currency', 'value'])

    # get original token exchange rate
    rpc = edpool.endpoint_by_chain()
    w3 = Web3(Web3.HTTPProvider(rpc))
    # get the default token name
    main_token, rate_dict[main_token], wrapped_token, rate_dict[wrapped_token] = get_main_token(chain, block_number - 1, w3)
    jsonlist = listdir(folder_prefix + '/invocation_tree')
    for i in jsonlist:
        file = open(folder_prefix + '/invocation_tree/' + i)

        # summary dict for this transaction
        summary_dict = {}
        traces = json.load(file)

        # memory for out of gas
        out_of_gas = False

        for trace in traces:
            # starting with reverted and out-of-gas check
            # event does not show successful status, only to see whether last call is successful
            if not out_of_gas:
                if trace['type'] == 'event':
                    event_name = trace["function"]
                    input_value = trace['input']

                    # event name as transfer refers to token transfer
                    if event_name.lower() == 'transfer' and len(input_value) != 0:
                        currency, decimal = get_currency(trace['address'], chain, block_number - 1, w3, rate_dict)
                        from_address, to_address, amount = find_address_transfer_event(trace, input_value)
                        if isinstance(amount, int):
                            value = amount / pow(10, decimal)
                            summary_dict = othertransfer(summary_dict, currency, from_address, to_address,
                                                         value, flow)

                    # event name as withdrawal refers to token withdraw
                    elif event_name.lower() == 'withdrawal' and trace['address'].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
                        currency, decimal = get_currency(trace['address'], chain, block_number - 1, w3, rate_dict)
                        from_address = input_value[0]
                        if len(trace['data']) == 2:
                            amount = trace['data'][1]
                        else:
                            amount = trace['data'][0]
                        if isinstance(amount, int):
                            summary_dict = othertransfer(summary_dict, currency, from_address, trace['address'],
                                                     amount / pow(10, decimal), flow)

                    # event name as deposit refers to token deposit
                    elif event_name.lower() == 'deposit' and trace['address'].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
                            currency, decimal = get_currency(trace['address'], chain, block_number - 1, w3, rate_dict)
                            to_address = input_value[0]
                            if len(trace['data']) == 2:
                                amount = trace['data'][1]
                            else:
                                amount = trace['data'][0]
                            if isinstance(amount, int):
                                summary_dict = othertransfer(summary_dict, currency, trace['address'], to_address,
                                                         amount / pow(10, decimal), flow)

            # for local token flow, there mostly is a trace with non-zero value
            if trace['type'] == 'call'  or trace['type'] == 'create' and trace["value"] != 0 and trace['status'] != "OutOfGas":
                    summary_dict = deal_transfer(summary_dict, main_token, trace, flow)

            if trace['type'] == 'selfdestruct' and trace["value"] != 0:
                    new_trace = {
                        'from': trace['address'],
                        'to': trace['refund_target'],
                        'value': trace['value']
                    }
                    summary_dict = deal_transfer(summary_dict, main_token, new_trace, flow)

            # Call is out of gas, so the following events are not available
            if trace['type'] == 'call' and trace['status'] == "OutOfGas":
                out_of_gas = True
            else:
                out_of_gas = False

        # If it has balance changes
        if len(summary_dict) != 0:

            # Process of getting exchange rate, currently not available
            for address in summary_dict.keys():
                address_balance = summary_dict[address]
                for token in address_balance:
                    value = address_balance[token]
                    rate = rate_dict[token]
                    address_balance[token] = [value, value * rate]
            total_dict[transaction_hash] = summary_dict

    # Remove zeros and empty address
    total_dict = remove_zeros(total_dict)

    os.makedirs(folder_prefix + '/token_info', exist_ok=True)
    if transaction_hash in total_dict:
        inner_dict = total_dict[transaction_hash]
        # Ensure all keys in inner_dict are strings
        inner_dict = {str(k): v for k, v in inner_dict.items()}
    else:
        inner_dict = {}


    special_keys = [o_from_add, o_to_add]  # Keys to prioritize

    # Custom sorting
    total_dict[transaction_hash] = dict(
        sorted(
            inner_dict.items(),
            key=lambda item: (
                item[0] not in special_keys,  # First, ensure special keys come first
                list(inner_dict.keys()).index(item[0]) if item[0] in special_keys else float('inf'),
                # Maintain original order for special keys
                item[0]  # Sort other keys alphabetically
            )
        )
    )
    # dump balance and tokenflow
    with open(folder_prefix + '/token_info/balance.json', 'w') as json_file:
        json.dump(total_dict, json_file, indent=2)
    flow.to_json(folder_prefix + '/token_info/tokenflow.json', orient='records', indent=2)

    with open(folder_prefix + '/token_info/rate_dict.json', 'w') as json_file2:
        json.dump(rate_dict, json_file2, indent=2)

    currency_dict = get_currency_dict()

    with open(folder_prefix + '/token_info/currency_dict.json', 'w') as json_file3:
        json.dump(currency_dict, json_file3, indent=2)

    return main_token
