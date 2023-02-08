from main import prepare_web3, process_tx, classify_address
import leveldb
import fasttext
import fasttext.util
import numpy as np
import re
import torch
import torch.nn as nn
import torch.nn.functional as F

class LogEmbedding(nn.Module):

    def __init__(self, fn_size, pa_size) -> None:
        super(LogEmbedding, self).__init__()
        self.para_weight = nn.Linear(pa_size, fn_size)

    # function_name and parameters are torch.tensor
    def forward(self, function_name, parameters):
        if function_name.dim() == 1:
            function_name.unsqueeze(0)
        if parameters.dim() == 1:
            parameters.unsqueeze(0)

        x = self.para_weight(parameters.float())

        #  connect function_name with parameters
        x = torch.cat((x, function_name), 0)

        return x


address_type = {'ERC20':1, 'ERC721':2, 'ERC1155':3, 'Unknown':4}

w3 = prepare_web3()
event_db = leveldb.LevelDB('db/event_db')

addr_list, decoded_logs = process_tx(w3, '0x015b2b4858e8be25a2fdcfb7697709a6d9f2dcb42bcc0c0dad4763e36f98e619', event_db)
assert not (decoded_logs == ['Unknown Event'])

fasttext.util.download_model('en', if_exists='ignore')
model = fasttext.load_model('cc.en.300.bin')
# log
# AttributeDict({'address': '0xdAC17F958D2ee523a2206206994597C13D831ec7', 'blockHash': HexBytes('0x39d88daafb66b3bc7553086437bc143d1bb7ddb8c7c305488aa709dfff9c19ae'),
# 'blockNumber': 16424933, 'data': '0x0000000000000000000000000000000000000000000000000000000007270e00', 'logIndex': 76, 'removed': False,
# 'topics': [HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'), HexBytes('0x0000000000000000000000005c65a9df43080a388071adfdd2ce2f94ad30e3b5'),
# HexBytes('0x000000000000000000000000e9709135f4e391e240867c23b09b0a43f404e68a')],
# 'transactionHash': HexBytes('0x015b2b4858e8be25a2fdcfb7697709a6d9f2dcb42bcc0c0dad4763e36f98e619'), 'transactionIndex': 14})

for log in decoded_logs:

    # extract funtion name, function structure and parameters
    # In this step, we don't conside unbounded arrays and strings, we will deal with that later
    function_signature = log[0]     # Transfer(address,address,uint256)
    parameters = log[1]             # ['0x5c65a9df43080a388071adfdd2ce2f94ad30e3b5', '0xe9709135f4e391e240867c23b09b0a43f404e68a', 120000000]
    parameters_size = len(parameters)

    # after using some regular expression method, we get the function name and function structure from function signature
    function_name = 'Transfer'
    function_structure = ['address', 'address', 'uint256']

    # Before vectorize the function name, we need to build a model for function name
    # In this part, we assume that we already have a well trained model for function name
    fn_vector = model.get_sentence_vector(function_name)
    # print(type(fn_vector))      # numpy.ndarray
    # print(len(fn_vector))       # 300

    # for address, we use its category
    for i in range(parameters_size):
        if function_structure[i] == 'address':
            parameters[i] = address_type[classify_address(w3, w3.toChecksumAddress(parameters[i]))]
            # parameters = np.array([4, 4, 120000000])

    parameters_vector = np.array(parameters)

    # put fn_vector and parameter_vector together

    # create some weight matrixs
    fn_size = np.size(fn_vector)

    v1 = torch.from_numpy(fn_vector)
    v2 = torch.from_numpy(np.array(parameters))

    model = LogEmbedding(fn_size, parameters_size)
    result = model.forward(v1, v2)
