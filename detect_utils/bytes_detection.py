import math
from detect_utils.tools import load_json

basic_limits = load_json("detect_utils/basic_limits.json")  # Gas limit restriction

def cosine_similarity(v1, v2):
    # Compute dot product
    dot_product = v1[0] * v2[0] + v1[1] * v2[1]

    # Compute magnitudes
    magnitude_v1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
    magnitude_v2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)

    if sum(v1) == 0 and sum(v2) == 0:
        return 1
    elif sum(v1) == 0 or sum(v2) == 0:
        return 0
    return dot_product / (magnitude_v1 * magnitude_v2)

# Define your detection function
def detect_tx(transaction):
    recipient = transaction['to']
    if recipient == "empty":
        return True
    tx_type = transaction["4byteData"]
    if isinstance(tx_type, str) and len(tx_type) == 10:
        if tx_type in basic_limits:
            avg_vector = basic_limits[tx_type]["avg_vector"]
            tx_vector = [transaction["zeroCount"], transaction["oneCount"]]
            cosine = cosine_similarity(tx_vector, avg_vector)
            limits = basic_limits[tx_type]["outlier_cosine"]
            extracted = True
            for upper in limits:
                if float(upper) >= cosine >= float(limits[upper]):
                    tx_gas = transaction["gasUsed"]
                    extracted = tx_gas > basic_limits[tx_type]["gas_limit"]
            return extracted
        else:
            return True
    else:
        return False

def detect_4bytes(basic_info):
    # Apply the detection function
    basic_info['type_output'] = basic_info.apply(detect_tx, axis=1)

    # Get the list of transaction hashes where type_output is True
    suspicious_list = basic_info.loc[basic_info['type_output'] == True, 'hash'].tolist()

    return suspicious_list