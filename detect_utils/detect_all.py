from detect_utils.rule_cyclic_calls import detect_cyclic_transaction
from detect_utils.rule_flashloan import detect_flashloan_transaction
from detect_utils.rule_token_supply import detect_token_supply
from detect_utils.rule_access_control import detect_access_control
from detect_utils.tools import check_balance, check_balance_all

# Combine all detections in detect_utils
def rule_based_detection(tx_hash, gas_used, from_address, to_address, folder_prefix):

    detection_result = False
    reason = []

    if detect_cyclic_transaction(tx_hash,gas_used, from_address, to_address, folder_prefix):
        print('Suspicious Reentrancy Attack Detected')  # To be updated
        detection_result = True
        reason.append('Suspicious Reentrancy Attack Detected')

    if detect_flashloan_transaction(tx_hash, gas_used, from_address, to_address, folder_prefix):
        print('Suspicious Flashloan Attack Detected')  # To be updated
        detection_result = True
        reason.append('Suspicious Flashloan Attack Detected')

    if detect_token_supply(tx_hash, folder_prefix):
        print('Token Supply Abrupt Changes Detected')  # To be updated
        detection_result = True
        reason.append('Token Supply Abrupt Changes Detected')

    if detect_access_control(tx_hash, folder_prefix):
        print('Lack Access Control Detected')  # To be updated
        detection_result = True
        reason.append('Lack Access Control Detected')

    la_tx = False
    # 63k USD and 27k for sender and receiver, the hard margin of SVM
    if check_balance_all(tx_hash, folder_prefix, 63000):
        print('Large Amount Transaction')
        la_tx = True
    elif check_balance(tx_hash, folder_prefix, from_address, 27000):
        print('From Address Amount Transaction')
        la_tx = True
    elif check_balance(tx_hash, folder_prefix, to_address, 27000):
        print('To Address Large Amount Transaction')
        la_tx = True

    return detection_result, reason, la_tx
