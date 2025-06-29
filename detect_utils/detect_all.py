import json
from detect_utils.rule_cyclic_calls import detect_cyclic_transaction
from detect_utils.rule_flashloan import detect_flashloan_transaction
from detect_utils.rule_token_supply import detect_token_supply
from detect_utils.deprecated_rule_access_control import detect_access_control
from detect_utils.tools import check_balance, check_balance_all, check_total_supply, separate_balance, self_created, flow_in

# Combine all detections in detect_utils
def rule_based_detection(tx_hash, selected_tx_dict, is_nft, folder_prefix):
    from_address = selected_tx_dict['from']
    to_address = selected_tx_dict['to']
    gas_used = selected_tx_dict['gasUsed']
    tx_timestamp = selected_tx_dict['timestamp']

    rule_detection_result = False
    reason = []

    if detect_cyclic_transaction(tx_hash, gas_used, from_address, to_address, folder_prefix):
        print('Suspicious Reentrancy Attack Detected')  # To be updated
        rule_detection_result = True
        reason.append('Suspicious Reentrancy Attack Detected')

    if detect_flashloan_transaction(tx_hash, gas_used, from_address, to_address, folder_prefix):
        print('Suspicious Flashloan Attack Detected')  # To be updated
        rule_detection_result = True
        reason.append('Suspicious Flashloan Attack Detected')

    if detect_token_supply(tx_hash, folder_prefix):
        print('Token Supply Abrupt Changes Detected')  # To be updated
        rule_detection_result = True
        reason.append('Token Supply Abrupt Changes Detected')

    # if detect_access_control(tx_hash, folder_prefix):
    #     print('Lack Access Control Detected')  # To be updated
    #     reason.append('Lack Access Control Detected')

    la_tx = False

    detect_self_create = self_created(selected_tx_dict)
    separated_balance = separate_balance(tx_hash, tx_timestamp, folder_prefix, from_address, to_address)
    detect_flow_in, detect_token_thief, flow_in_type = flow_in(separated_balance, is_nft)
    sender_list = list(separated_balance['sender'].keys())
    trader_list = list(separated_balance['trader'].keys())
    checking_list = list(set(sender_list + trader_list))


    # if check_total_supply(tx_hash, folder_prefix, 0.3):
    #     print('Very large compared with total supply')  # To be updated
    #     reason.append('Large Amount Compared with Total Supply')

    # 63k USD and 27k for sender and receiver, the hard margin of SVM
    if check_balance_all(tx_hash, checking_list, folder_prefix, 63000):
        print('Large Amount Transaction')
        la_tx = True
    elif check_balance(tx_hash, folder_prefix, from_address, 27000):
        print('From Address Amount Transaction')
        la_tx = True
    elif check_balance(tx_hash, folder_prefix, to_address, 27000):
        print('To Address Large Amount Transaction')
        la_tx = True

    # At least two flags means attack
    filter_result = sum([detect_self_create, detect_flow_in, detect_token_thief, la_tx, rule_detection_result]) >= 2
    flags = [detect_self_create, la_tx, rule_detection_result]
    flag_names = ['detect_self_create', 'la_tx', 'rule_detection_result']
    # Get a list of which ones are True
    true_flags = [name for name, flag in zip(flag_names, flags) if flag]
    if flow_in_type:
        true_flags.append(flow_in_type)

    return filter_result, true_flags, reason, la_tx
