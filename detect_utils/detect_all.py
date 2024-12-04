from detect_utils.rule_cyclic_calls import detect_cyclic_transaction
from detect_utils.rule_flashloan import detect_flashloan_transaction
from detect_utils.rule_token_supply import detect_token_supply
from detect_utils.rule_access_control import detect_access_control

# Combine all detections in detect_utils
def rule_based_detection(tx_hash, chain):

    detection_result = False
    reason = []

    if detect_cyclic_transaction(tx_hash, chain):
        print('Suspicious Reentrancy Attack Detected')  # To be updated
        detection_result = True
        reason.append('Suspicious Reentrancy Attack Detected')

    if detect_flashloan_transaction(tx_hash, chain):
        print('Suspicious Flashloan Attack Detected')  # To be updated
        detection_result = True
        reason.append('Suspicious Flashloan Attack Detected')

    if detect_token_supply(tx_hash, chain):
        print('Token Supply Abrupt Changes Detected')  # To be updated
        detection_result = True
        reason.append('Token Supply Abrupt Changes Detected')

    if detect_access_control(tx_hash, chain):
        print('Lack Access Control Detected')  # To be updated
        detection_result = True
        reason.append('Lack Access Control Detected')

    return detection_result, reason
