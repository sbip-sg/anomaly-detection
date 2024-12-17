import json
from web3 import Web3

# Abi file to call contract for symbol and decimals
abi_file = open("utils/erc20.abi.json")
abi = json.load(abi_file)

# dict to store currency symbol and decimals
currency_dict = {}

uniswap_file = open("utils/uniswapv2.abi.json")
uniswap = json.load(uniswap_file)

def get_rate(address, block_number, w3, decimal, rate_dict):
    # uniswap v2 address
    contract_address = '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'
    contract = w3.eth.contract(address=contract_address, abi=uniswap)

    # warped ether
    if address == '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2':
        # USDT
        second_address = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
    else:
        # warped ether
        second_address = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'

    # Get contract sawp amount
    method = contract.functions.getAmountsOut(pow(10, decimal), [address, second_address])
    result = method.call(block_identifier=block_number)

    # warped ether to USDT
    if address == '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2':
        return result[1] / 1e6
    else:
        # token to warped ether to USDT
        return rate_dict['ETH'] * result[1] / 1e18

# Get the currency symbol and decimals by the contract
def get_currency(hash, block_number, rpc, rate_dict):
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
            if 'usd' in currency.lower() and len(currency.lower()) <= 6:
                exchange_rate = 1
            elif 'eth' in currency.lower() and len(currency.lower()) <= 6:
                exchange_rate = rate_dict['ETH']
            else:
                # Get exchange rate
                exchange_rate = get_rate(address, block_number, w3, decimal)
        except Exception as e:
            print('Error: can not get transfer currency', hash.lower())
            currency = hash
            decimal = 0
            exchange_rate = 0
        currency_dict[hash] = (currency, decimal, exchange_rate)
        rate_dict[currency] = exchange_rate
    else:
        (currency, decimal, exchange_rate) = currency_dict[hash]
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