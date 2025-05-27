from detect_utils.tools import load_json

gas_limits = load_json("detect_utils/gas_limit.json")  # Gas limit restriction

# Define your detection function
def detect_tx(transaction):
    if transaction['status'] == 0:
        return False
    recipient = transaction['to']
    if recipient == "empty":
        return True
    elif (transaction['to_creator'] ==  transaction['from'] and int(transaction["timestamp"])
          - int(transaction["to_timestamp"]) < 600000):
        return True
    elif transaction['to_is_eoa'] or not transaction['code_created']:
        return False

    tx_type = transaction["4byteData"]
    if isinstance(tx_type, str) and len(tx_type) == 10:
        if tx_type in gas_limits:
            tx_gas = transaction["gasUsed"]
            return tx_gas > gas_limits[tx_type]
        else:
            return True
    else:
        return False

def detect_4bytes(basic_info):
    # Apply the detection function
    basic_info['type_output'] = basic_info.apply(detect_tx, axis=1)

    # Get the list of transaction hashes where type_output is True
    suspicious_txs = basic_info.loc[basic_info['type_output'] == True]
    # suspicious_list = suspicious_txs.nlargest(3, 'gasUsed')['hash'].tolist()
    suspicious_list = suspicious_txs['hash'].tolist()

    return suspicious_list