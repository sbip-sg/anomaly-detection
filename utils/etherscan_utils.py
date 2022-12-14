import datetime
import json
import requests
def get_block_num(dt):
    timeStamp = int(dt.timestamp())
    block_endpoint = f"https://api.etherscan.io/api?module=block&action=getblocknobytime&timestamp={timeStamp}&closest=before&apikey=BHJV4F9VUKS3ETFQ75NVJKGX97Z9SYKRBD"
    block_json = json.loads(requests.get(block_endpoint).text)
    return int(block_json['result'])

def get_passed_blocks_in_days(delta_day = 7):
    from_block = get_block_num(datetime.datetime.now() - datetime.timedelta(delta_day))
    to_block = get_block_num(datetime.datetime.now())
    return from_block, to_block

def get_event_from_etherscan(contract_address , abi_token='BHJV4F9VUKS3ETFQ75NVJKGX97Z9SYKRBD'):
    abi_endpoint = f"https://api.etherscan.io/api?module=contract&action=getabi&address={contract_address}&apikey={abi_token}"
    abi = json.loads(requests.get(abi_endpoint).text)
    if abi['status'] == '0':
        return {}
    # print("abi =", abi)
    contract = w3.eth.contract(contract_address, abi=abi["result"])
    receipt_event_signature_hex = w3.toHex(log["topics"][0])
    abi_events = [abi for abi in contract.abi if abi["type"] == "event"]
    for event in abi_events:
        # Get event signature components
        name = event["name"]
        inputs = [param["type"] for param in event["inputs"]]
        inputs = ",".join(inputs)
        # Hash event signature
        event_signature_text = f"{name}({inputs})"
        event_signature_hex = w3.toHex(w3.keccak(text=event_signature_text))
        # Find match between log's event signature and ABI's event signature
        if event_signature_hex == receipt_event_signature_hex:
            # Decode matching log
            decoded_log = contract.events[event["name"]]().processReceipt(receipt, errors=DISCARD)
            topic = name + '(' + inputs + ')'
            database[event_signature_hex] = topic
            decoded_logs.append(decoded_log)
    return database
