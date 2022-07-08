# util functions, process + classify address based on function signatures 
import json
from eth_utils import to_hex
# define the list of classes + coressponding signature file 
signature_files = {
                    "ERC20": 'signature_data/erc20_signature.json'
                }
# Special case when address is a proxy 
proxy_signature = '5c60da1b' # implementation()
# not the optimal way of doing this because we load json file everytime.
# in the future after determined + processed all classes signatures
# we can put these signatures in some constants variable
def classify_address(w3,address):
    matching_results = {}
    matched_result = 'Not Identified'
    matched_perc = 0
    byte_code = to_hex(w3.eth.get_code(address))
    for key_ in signature_files.keys():
        file_ = open(signature_files[key_])
        signatures = json.load(file_)
        match_count = 0
        for item in signatures:
            if (item in byte_code):
                match_count += 1
        if match_count/len(signatures) > matched_perc:
            matched_perc = match_count/len(signatures) 
            matched_result = key_
        matching_results[key_] = match_count/len(signatures)
    print (f" found matched results {matched_result} {matched_perc*100}% identical ")
    #check proxy
    if matched_result == 'Not Identified' and proxy_signature in byte_code:
        implementation_addr = '0x00'
        # need to send tx with data "5c60da1b" to the proxy address.
        # the unstructured proxy stores the impelemntation address at a location where we can get from source code
        # https://ethereum.stackexchange.com/questions/103143/how-do-i-get-the-implementation-contract-address-from-the-proxy-contract-address
        # https://eips.ethereum.org/EIPS/eip-1967#logic-contract-address
        implementation_addr = w3.eth.call({'value': 0, 'gas': 100000, 
                                            'to': address,
                                                'data': '0x'+proxy_signature})
        print ("implementation found ", implementation_addr)

    print ("debug ", matching_results)
    return matched_result
