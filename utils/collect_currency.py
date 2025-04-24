import json

from mpmath import power
from web3 import Web3

def load_json(filepath):
    """Utility function to load a JSON file safely."""
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)

# Load ABI files and token info using the function
abi = load_json("utils/erc20.abi.json")  # ABI for ERC-20 contract
uniswap = load_json("utils/uniswapv2.abi.json")  # ABI for UniswapV2
chain_info = load_json("utils/chain_token_dict.json")  # Token info for all chains

# Dict to store currency addresses to names, decimals and exchange rates
currency_dict = {}

# list to store collected currency names
currency_address = {}

# Interface IDs
ERC721_INTERFACE_ID = "0x80ac58cd"
ERC1155_INTERFACE_ID = "0xd9b67a26"

# Minimal ERC-165 ABI to call supportsInterface
erc165_abi = [{
    "constant": True,
    "inputs": [{"name": "interfaceID", "type": "bytes4"}],
    "name": "supportsInterface",
    "outputs": [{"name": "", "type": "bool"}],
    "type": "function",
}]

# Dict to store NFT address
NFT_dict = {}

def is_NFT(contract_address, w3):
    contract = w3.eth.contract(address=contract_address, abi=erc165_abi)

    try:
        is_erc721 = contract.functions.supportsInterface(ERC721_INTERFACE_ID).call()
        is_erc1155 = contract.functions.supportsInterface(ERC1155_INTERFACE_ID).call()
        return bool(is_erc721) or bool(is_erc1155)
    except:
        return False

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

    # Ensure decimals are reduced in the same scale but not below 12
    min_decimal = 12
    if decimal > min_decimal:
        scale_factor = min(decimal, wrapped_decimal) - min_decimal
        decimal -= scale_factor
        wrapped_decimal -= scale_factor

    # Get contract swap amount
    try:
        method = contract.functions.getAmountsIn(pow(10, wrapped_decimal), [address, wrapped_address])
        result = method.call(block_identifier=block_number)

    except Exception as e:
        print('uniswap error:', e, [address, wrapped_address])
        return 0


    # token to warped ether to USDT
    (_, _ , exchange_rate, _) = currency_dict[wrapped_address.lower()]
    token_rate = exchange_rate * pow(10, decimal) / result[0]
    if token_rate < 150000:
        return token_rate
    else:
        return 0

# Get the currency symbol and decimals by the contract
def get_currency(address, chain, block_number, w3, rate_dict):
    if address in NFT_dict:
        return NFT_dict[address], 0, True, 0
    address = address.lower()
    if address not in currency_dict:
        checksum_address = Web3.to_checksum_address(address)
        contract = w3.eth.contract(
            address=checksum_address,
            abi=abi,
        )
        try:
            # Get symbol
            currency = contract.functions.symbol().call()
            if currency in currency_address and currency_address[currency] != address:
                currency = f'{currency}_{address}'
            else:
                currency_address[currency] = address
        except Exception as e:
            print('Error:', e, ' ,can not get transfer currency symbol', address)
            currency = address

        try:
            # Get decimals
            decimal = contract.functions.decimals().call()
            total_supply = contract.functions.totalSupply().call()
        except Exception as e:
            if is_NFT(checksum_address, w3):
                NFT_dict[address] = currency
                return currency, 0, True, 0
            print('Error:', e, ' ,can not get transfer currency decimal', address)
            decimal = 0
            total_supply = 0

        try:
            # Get exchange rate
            checksum_address = Web3.to_checksum_address(address)
            exchange_rate = get_rate(checksum_address, chain, block_number, w3, decimal)
        except Exception as e:
            print('Error:', e, ',can not get exchange_rate', address)
            exchange_rate = 0
        currency_dict[address] = (currency, decimal, exchange_rate, total_supply/pow(10, decimal))
        rate_dict[currency] = exchange_rate
    else:
        (currency, decimal, exchange_rate, _) = currency_dict[address]
    return currency, decimal, False, exchange_rate

def get_main_token(chain, block_number, w3):
    chain_token_info = chain_info[chain]
    chain_token = chain_token_info['chainToken']
    contract_address = chain_token_info['uniswapV2Address']
    usdc_address = chain_token_info['usdcAddress']
    wrapped_token = chain_token_info['wrappedToken']
    wrapped_address = chain_token_info['wrappedAddress']
    usdc_decimal = chain_token_info['usdc_decimal']
    wrapped_decimal = chain_token_info['wrapped_decimal']

    wrapped_contract = w3.eth.contract(
        address=wrapped_address,
        abi=abi,
    )
    wrapped_total_supply = wrapped_contract.functions.totalSupply().call()
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

    currency_dict[chain_token] = (chain_token, wrapped_decimal, exchange_rate, 1e20)
    currency_dict[wrapped_address.lower()] = (wrapped_token, wrapped_decimal, exchange_rate, wrapped_total_supply/pow(10, wrapped_decimal))

    return chain_token, exchange_rate, wrapped_token, exchange_rate

def get_currency_dict():
    return currency_dict