import json
import pandas as pd
from os import listdir
from web3 import Web3
from utils.get_rate import get_rate

# Abi file to call contract for symbol and decimals
abi_file = open("utils/erc20.abi.json")
abi = json.load(abi_file)

# dict to store currency symbol and decimals
currency_dict = {}

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


# Get the currency symbol and decimals by the contract
def get_currency(hash, rpc):
    hash = hash.lower()
    if hash not in currency_dict:
        w3 = Web3(Web3.HTTPProvider(rpc))
        try:
            address = Web3.to_checksum_address(hash)
            contract = w3.eth.contract(
                address=address,
                abi=abi,
            )
            # Get symbol
            currency = contract.functions.symbol().call()
            # Get decimals
            decimal = contract.functions.decimals().call()
        except Exception as e:
            print('Error: can not get transfer currency', hash.lower())
            currency = hash
            decimal = 0
        currency_dict[hash] = (currency, decimal)
    else:
        (currency, decimal) = currency_dict[hash]
    return currency, decimal


# Build a function to inject information to a summary dict
def update_summary(summary, address, currency, amount):
    # if new address
    if address not in summary:
        summary[address] = {}

    # if new currency
    if currency not in summary[address]:
        summary[address][currency] = 0

    # calculate changes
    summary[address][currency] += amount
    return summary


# Function to handle other-token transfer transactions
def othertransfer(summary, currency, from_address, to_address, amount, flow):
    # Delete from from-address
    summary = update_summary(summary, from_address, currency, -amount)
    # Add to to-address
    summary = update_summary(summary, to_address, currency, amount)
    # Input transfer to dataframe flow
    if amount != 0:
        flow.loc[len(flow)] = [from_address, to_address, currency, amount]

    return summary


# Function to deal with local-token transfer transactions
def deal_transfer(summary, currency, trace, flow):
    from_address = trace["from"]
    to_address = trace["to"]
    amount = trace["value"] / 1e18

    summary = update_summary(summary, from_address, currency, -amount)
    summary = update_summary(summary, to_address, currency, amount)
    if amount != 0:
        flow.loc[len(flow)] = [from_address, to_address, currency, amount]

    return summary


# This function is from observation and would be less reliable
# Function to find the address and amount from an event
def find_address_transfer_event(trace, input):
    # from address is normally the first of the inputs
    if (trace['address'] == '0x82af49447d8a07e3bd95bd0d56f35241523fbab1' and
            input[0] == '0x0000000000000000000000000000000000000000'):
        from_address = trace['address']
    else:
        from_address = input[0]

    # If an event have more than 2 inputs, the second would be to address and the third would be amount
    if len(input) > 2:
        to_address = input[1]
        amount = input[2]

    # If an event have 2 inputs and have data, amount is normally data and the second input would be to address
    elif len(input) == 2 and trace['data']:
        amount = trace['data'][0]
        to_address = input[1]
    elif len(input) == 2:
        from_address = '0x' + '0' * 40
        to_address = input[0]
        amount = 1
    # If an event have less than 2 inputs and have data, this transfer may be from null.
    elif trace['data']:
        amount = trace['data'][0]
        from_address = trace['address']
        to_address = input[0]

    # if have no information, ignore it.
    else:
        amount = 0
        to_address = '0x' + '0' * 40
    return from_address, to_address, amount


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
def collect_token(time_stamp, edpool, folder_prefix):
    # collect balance change of each transaction
    total_dict = {}

    # get the default token name
    token = chain_dict[edpool.chain]

    # collect token flows of each transaction
    flow = pd.DataFrame(columns=['from', 'to', 'currency', 'value'])
    rpc = edpool.endpoint_by_chain()
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
                    if event_name.lower() == 'transfer':
                        currency, decimal = get_currency(trace['address'], rpc)
                        from_address, to_address, amount = find_address_transfer_event(trace, input)
                        if isinstance(amount, int):
                            value = amount / pow(10, decimal)
                            summary_dict = othertransfer(summary_dict, currency, from_address, to_address,
                                                         value, flow)

                    # event name as withdrawal refers to token withdraw
                    elif event_name.lower() == 'withdrawal' and trace['address'].lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
                        currency, decimal = get_currency(trace['address'], rpc)
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
                            currency, decimal = get_currency(trace['address'], rpc)
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
                    rate = get_rate(time_stamp, token)
                    address_balance[token] = [value, value * rate]
            total_dict[transaction_hash] = summary_dict

    # Remove zeros and empty address
    total_dict = remove_zeros(total_dict)

    # dump balance and tokenflow
    with open(folder_prefix + '/balance.json', 'w') as json_file:
        json.dump(total_dict, json_file, indent=2)
    flow.to_json(folder_prefix + '/tokenflow.json', orient='records', indent=2)
