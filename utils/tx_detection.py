import os
from utils.get_traces import collect_trace
from utils.decode_trace import decode_trace_json
from utils.token_info import collect_token
from utils.generate_output import generate_output
from utils.tools import get_contract_info
from detect_utils.detect_all import rule_based_detection
from detect_utils.chatgpt_detect import chatgpt_detect
import json
import time

def tx_detect(tx_hash, chain, block_number, folder_prefix, selected_tx_dict, edpool, mev_bots, llm_detect):
    tx_time_dict = {}
    tx_detail_start_time = time.time()
    # Collect traces (raw invocation tree)
    tx_folder_prefix = f"{folder_prefix}/{tx_hash}"
    os.makedirs(tx_folder_prefix, exist_ok=True)
    collect_trace(tx_hash, edpool, tx_folder_prefix)
    foundry_end_time = time.time()
    tx_time_dict['foundry'] = foundry_end_time - tx_detail_start_time
    # Decode trace JSON and extract information from invocation tree
    decode_trace_json(tx_hash, tx_folder_prefix)
    decode_end_time = time.time()
    tx_time_dict['decode'] = decode_end_time - foundry_end_time
    if selected_tx_dict:
        from_address = selected_tx_dict['from']
        to_address = selected_tx_dict['to']
        gas_used = selected_tx_dict['gasUsed']

        main_token, nft_transaction, address_list = collect_token(tx_hash, chain, from_address, to_address,
                                                    int(block_number), edpool, tx_folder_prefix)
        address_json_path = f"{folder_prefix}/{tx_hash}/token_info/address_dict.json"
        get_contract_info(address_list, address_json_path)
        token_end_time = time.time()
        tx_time_dict['token'] = token_end_time - decode_end_time
        if to_address.lower() not in mev_bots:
            detection_result, reason, la_tx = rule_based_detection(tx_hash, selected_tx_dict["timestamp"], gas_used,
                                                                   from_address, to_address, tx_folder_prefix)
            selected_tx_dict['NFT_transaction'] = nft_transaction
            selected_tx_dict["detection_result"] = detection_result
            selected_tx_dict["reason"] = reason
            selected_tx_dict["la_tx"] = la_tx
        else:
            selected_tx_dict['NFT_transaction'] = False
            selected_tx_dict["detection_result"] = False
            selected_tx_dict["reason"] = ['To address as MEV Bot']
            selected_tx_dict["la_tx"] = False
        rule_end_time = time.time()
        tx_time_dict['rule_based'] = rule_end_time - token_end_time
        if selected_tx_dict["detection_result"] or selected_tx_dict["la_tx"]:
            generate_output(tx_hash, chain, selected_tx_dict, tx_folder_prefix, main_token)
            if llm_detect:
                score = chatgpt_detect(tx_hash, tx_folder_prefix)
                selected_tx_dict['llm_score'] = score
        with open(tx_folder_prefix + f"/basic_info_{tx_hash}.json", "w") as json_file:
            json.dump(selected_tx_dict, json_file, indent=2)
        output_end_time = time.time()
        tx_time_dict['output'] = output_end_time - rule_end_time

    return tx_time_dict
    