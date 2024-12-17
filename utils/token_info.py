import json
import pandas as pd
from os import listdir
from web3 import Web3
from utils.collect_transfer import get_rate, get_currency, find_address_transfer_event, deal_transfer, othertransfer

# Chain-currency dict
# getting the default currency is by value, so we need prior knowledge of tokens
chain_dict = {
    "arbitrum": "ETH",
    "avalanche": "AVAX",
    "base": "ETH",
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
def collect_token(block_number, edpool, folder_prefix):
    # collect balance change of each transaction
    total_dict = {}

    # get the default token name
    token = chain_dict[edpool.chain]
    # collect token flows of each transaction
    flow = pd.DataFrame(columns=['from', 'to', 'currency', 'value'])

    # get original token exchange rate
    rpc = edpool.endpoint_by_chain()
    w3 = Web3(Web3.HTTPProvider(rpc))
    rate_dict[token] = get_rate('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', block_number, w3, decimal=18, rate_dict = rate_dict)
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
                    input = trace['input']

                    # event name as transfer refers to token transfer
                    if event_name.lower() == 'transfer' and len(input) != 0:
                        currency, decimal = get_currency(trace['address'], block_number - 1, rpc)
                        from_address, to_address, amount = find_address_transfer_event(trace, input)
                        if isinstance(amount, int):
                            value = amount / pow(10, decimal)
                            summary_dict = othertransfer(summary_dict, currency, from_address, to_address,
                                                         value, flow)

                    # event name as withdrawal refers to token withdraw
                    elif event_name.lower() == 'withdrawal' and trace['address'].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
                        currency, decimal = get_currency(trace['address'], block_number - 1, rpc)
                        from_address = input[0]
                        if len(trace['data']) == 2:
                            amount = trace['data'][1]
                        else:
                            amount = trace['data'][0]
                        if isinstance(amount, int):
                            summary_dict = othertransfer(summary_dict, currency, from_address, trace['address'],
                                                     amount / pow(10, decimal), flow)

                    # event name as deposit refers to token deposit
                    elif event_name.lower() == 'deposit' and trace['address'].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
                            currency, decimal = get_currency(trace['address'], block_number - 1, rpc)
                            to_address = input[0]
                            if len(trace['data']) == 2:
                                amount = trace['data'][1]
                            else:
                                amount = trace['data'][0]
                            if isinstance(amount, int):
                                summary_dict = othertransfer(summary_dict, currency, trace['address'], to_address,
                                                         amount / pow(10, decimal), flow)
            if trace['type'] == 'call' or trace['type'] == 'staticcall' or trace['type'] == 'create' and trace['status'] != "OutOfGas":

                # for local token flow, there mostly is a trace with non-zero value
                if trace['type'] == 'call' or trace['type'] == 'staticcall' or trace['type'] == 'create' and trace["value"] != 0:
                    summary_dict = deal_transfer(summary_dict, token, trace, flow)

            # Call is out of gas, so the following events are not available
            if trace['type'] == 'call' and trace['status'] == "OutOfGas":
                out_of_gas = True
            else:
                out_of_gas = False

        # If it has balance changes
        if len(summary_dict) != 0:

            # Process of getting exchange rate, currently not available
            transaction_hash = i.split("_")[2].split(".")[0]
            for address in summary_dict.keys():
                address_balance = summary_dict[address]
                for token in address_balance:
                    value = address_balance[token]
                    rate = rate_dict[token]
                    address_balance[token] = [value, value * rate]
            total_dict[transaction_hash] = summary_dict

    # Remove zeros and empty address
    total_dict = remove_zeros(total_dict)

    # dump balance and tokenflow
    with open(folder_prefix + '/balance.json', 'w') as json_file:
        json.dump(total_dict, json_file, indent=2)
    flow.to_json(folder_prefix + '/tokenflow.json', orient='records', indent=2)
