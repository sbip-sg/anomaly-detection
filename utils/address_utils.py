# util functions, process + classify address based on function signatures
import json
from eth_utils import to_hex
# define the list of classes + coressponding signature file
signature_files = {
                    "ERC20": 'signature_data/erc20_signature.json',
                    "ERC721": 'signature_data/erc721_signature.json',
                    "ERC1155": 'signature_data/erc1155_signature.json'
                }
# default value at uinitialized storage slot
ZERO_ADDRESS = '0x' + '0'*40
# Special case when address is a proxy
proxy_signature = '5c60da1b' # implementation()
unknown = 'Unknown'
# not the optimal way of doing this because we load json file everytime.
# in the future after determined + processed all classes signatures
# we can put these signatures in some constants variable
def classify_address(w3,address):
    matching_results = {}
    matched_result = 'Not Identified'
    matched_perc = 0
    matched_num = 0
    byte_code = to_hex(w3.eth.get_code(address))
    if byte_code == '0x':
        return unknown
    for key_ in signature_files.keys():
        file_ = open(signature_files[key_])
        signatures = json.load(file_)
        match_count = 0
        for item in signatures:
            if (item in byte_code):
                match_count += 1
        if match_count/len(signatures) > matched_perc or (match_count/len(signatures) == matched_perc and matched_num < match_count):
            matched_perc = match_count/len(signatures)
            matched_result = key_
            matched_num = match_count
        matching_results[key_] = match_count/len(signatures)
    #check proxy

    if matched_result == 'Not Identified':
        print("This is a proxy contract")
        # need to send tx with data "5c60da1b" to the proxy address.
        # the unstructured proxy stores the impelemntation address at a location where we can get from source code
        # https://ethereum.stackexchange.com/questions/103143/how-do-i-get-the-implementation-contract-address-from-the-proxy-contract-address
        # https://eips.ethereum.org/EIPS/eip-1967#logic-contract-address

        # For fixed storage slot
        # storagePositions = [keccak256("org.zeppelinos.proxy.implementation,
        # bytes32(uint256(keccak256('eip1967.proxy.implementation')) - 1)),
        # keccak256("PROXIABLE") ]
        storage_positions = [ "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3",
                              "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",
                              "0xc5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7",
                              "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50",
                              "0x8c379a000000000000000000000000000000000000000000000000000000000"
                             ]
        implement_address = ZERO_ADDRESS
        # try every storage position until find the correct one
        fallback_func = "0x363d3d373d3d3d363d73"

        if fallback_func in byte_code:
            implement_address = '0x' + byte_code[22:22+40]
            implement_address = w3.toChecksumAddress(implement_address)
            matched_result = classify_address(w3, implement_address)
            return matched_result

        for storage_position in storage_positions:
            # find the implement address
            result = w3.eth.getStorageAt(address, storage_position)
            implement_address = '0x' + str(result.hex())[-40:]
            implement_address = w3.toChecksumAddress(implement_address)
            if implement_address != ZERO_ADDRESS:
                break
        if implement_address == ZERO_ADDRESS:
            try:
                implement_address = w3.eth.call({'value': 0, 'gas': 100000,
                                                'to': address,
                                                    'data': '0x'+proxy_signature})
            except Exception as e:
                print(e)
                return unknown
            if type (implement_address) is not str:
                implement_address = w3.toChecksumAddress(implement_address.hex()[-40:])
        print ("implementation found ", implement_address)
        matched_result = classify_address(w3, implement_address)
    else:
        print (f" found matched results {matched_result} {matched_perc*100}% identical ")
    return matched_result
