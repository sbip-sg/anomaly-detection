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
    #check proxy
    if matched_result == 'Not Identified' and proxy_signature in byte_code:
        print("This is a proxy contract")
        implementation_addr = '0x00'
        # need to send tx with data "5c60da1b" to the proxy address.
        # the unstructured proxy stores the impelemntation address at a location where we can get from source code
        # https://ethereum.stackexchange.com/questions/103143/how-do-i-get-the-implementation-contract-address-from-the-proxy-contract-address
        # https://eips.ethereum.org/EIPS/eip-1967#logic-contract-address

        # For fixed storage slot
        # storagePositions = [keccak256("org.zeppelinos.proxy.implementation", bytes32(uint256(keccak256('eip1967.proxy.implementation')) - 1))]
        storage_positions = [ "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3", 
                              "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"]

        # try every storage position until find the correct one
        for storage_position in storage_positions:
            # find the implement address
            result = w3.eth.getStorageAt(address, storage_position)
            implement_address = '0x' + str(result.hex())[-40:]
            implement_address = w3.toChecksumAddress(implement_address)
            try:
                matched_result = classify_address(w3, implement_address)
            except:
                continue
            else:
                # print("Implement address ", implement_address)
                break
                
        
        # implementation_addr = w3.eth.call({'value': 0, 'gas': 100000,
        #                                     'to': address,
        #                                         'data': '0x'+proxy_signature})
        
        # print ("implementation found ", implementation_addr)
    else:
        print (f" found matched results {matched_result} {matched_perc*100}% identical ")
    # print ("debug ", matching_results)
    return matched_result
