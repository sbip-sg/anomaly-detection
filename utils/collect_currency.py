import json
from web3 import Web3

def load_json(filepath):
    """Utility function to load a JSON file safely."""
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)

# Load ABI files and token info using the function
abi = load_json("utils/erc20.abi.json")  # ABI for ERC-20 contract
uniswap = load_json("utils/uniswapv2.abi.json")  # ABI for UniswapV2
chain_info = load_json("utils/chain_token_dict.json")  # Token info for all chains

# Dict to store currency symbol and decimals
currency_dict = {}

def reset_currency_dict():
    global currency_dict  # Refer to the outer dictionary
    currency_dict.clear()  # Clears the dictionary instead of reassigning it

def get_rate(address: str, chain: str, block_number: int, w3: any, decimal: int):
    # get chain info
    chain_token_info = chain_info[chain]
    contract_address = chain_token_info['uniswapV2Address']
    wrapped_address = chain_token_info['wrappedAddress']
    wrapped_decimal = chain_token_info['wrapped_decimal']
    # uniswap v2 address
    contract = w3.eth.contract(address=contract_address, abi=uniswap)

    # Get contract swap amount
    try:
        method = contract.functions.getAmountsIn(pow(10, wrapped_decimal), [address, wrapped_address])
        result = method.call(block_identifier=block_number)

    except Exception as e:
        print('uniswap error:', e, [address, wrapped_address])
        return 0


    # token to warped ether to USDT
    (_, _ , exchange_rate) = currency_dict[wrapped_address.lower()]
    return exchange_rate * pow(10, decimal) / result[0]

# Get the currency symbol and decimals by the contract
def get_currency(address, chain, block_number, w3, rate_dict):
    address = address.lower()
    if address not in currency_dict:
        try:
            checksum_address = Web3.to_checksum_address(address)
            contract = w3.eth.contract(
                address=checksum_address,
                abi=abi,
            )
            # Get symbol
            currency = contract.functions.symbol().call()
            # Get decimals
            decimal = contract.functions.decimals().call()
        except Exception as e:
            print('Error:', e, ' ,can not get transfer currency', address)
            currency = address
            decimal = 0

        try:
            if 'usd' in currency.lower() and len(currency.lower()) <= 6:
                exchange_rate = 1
            else:
                # Get exchange rate
                checksum_address = Web3.to_checksum_address(address)
                exchange_rate = get_rate(checksum_address, chain, block_number, w3, decimal)
        except Exception as e:
            print('Error:', e, ',can not get exchange_rate', address)
            exchange_rate = 0
        currency_dict[address] = (currency, decimal, exchange_rate)
        rate_dict[currency] = exchange_rate
    else:
        (currency, decimal, exchange_rate) = currency_dict[address]
    return currency, decimal

def get_main_token(chain, block_number, w3):
    chain_token_info = chain_info[chain]
    chain_token = chain_token_info['chainToken']
    contract_address = chain_token_info['uniswapV2Address']
    usdc_address = chain_token_info['usdcAddress']
    wrapped_token = chain_token_info['wrappedToken']
    wrapped_address = chain_token_info['wrappedAddress']
    usdc_decimal = chain_token_info['usdc_decimal']
    wrapped_decimal = chain_token_info['wrapped_decimal']
    # Ensure decimals are reduced in the same scale but not below 6
    min_decimal = 3
    scale_factor = min(usdc_decimal, wrapped_decimal) - min_decimal
    if scale_factor >= 0:
        usdc_decimal_new = usdc_decimal - scale_factor
        wrapped_decimal_new = wrapped_decimal - scale_factor
    else:
        usdc_decimal_new = usdc_decimal
        wrapped_decimal_new = wrapped_decimal

    contract = w3.eth.contract(address=contract_address, abi=uniswap)

    try:
        method = contract.functions.getAmountsOut(pow(10, usdc_decimal_new), [usdc_address, wrapped_address])
        result = method.call(block_identifier=block_number)
        exchange_rate = pow(10, wrapped_decimal_new) / result[1]
    except Exception as e:
        print('uniswap error:', e, [usdc_address, wrapped_address])
        exchange_rate = 0

    currency_dict[chain_token] = (chain_token, wrapped_decimal, exchange_rate)
    currency_dict[wrapped_address.lower()] = (wrapped_token, wrapped_decimal, exchange_rate)

    return chain_token, exchange_rate, wrapped_token, exchange_rate

def get_currency_dict():
    return currency_dict