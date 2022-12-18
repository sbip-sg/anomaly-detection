# process abi json file to a file with signatures for bytecode classification.
# the bytecode contains all the signatures => belong to the class
# we try not to rely on etherscan or the contract sourcecode, just bytecode querying from blockchain
import argparse
import json
from eth_utils import event_abi_to_log_topic, function_abi_to_4byte_selector, to_hex

def process_abi_to_signature(input_file, output_file):
    #assume input_file has only 1 contract
    input_file = open(input_file)
    interface = json.load(input_file)
    abi = list(interface['contracts'].values())[0]['abi']
    signatures = []
    for item in abi:
        if item['type'] == 'event':
            signatures.append(to_hex(event_abi_to_log_topic(item))[2:]) #convert to hex_str + remove 0x prefix
        if item['type'] == 'function':
            signatures.append(to_hex(function_abi_to_4byte_selector(item))[2:])
    #print (signatures)
    with open(output_file, 'w') as outfile:
        json.dump(signatures, outfile)

    return signatures


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, type=str, help="json file from solc --combined-json=abi  [your_file.sol] > [your_json_output_file]")
    parser.add_argument("-o", "--output", required=True, type=str, help="the json file output to write the function + event signatures to")
    args = parser.parse_args()

    process_abi_to_signature(args.input, args.output)