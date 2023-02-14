from main import prepare_web3, process_tx, classify_address, open_json
import leveldb
import fasttext
import fasttext.util
import numpy as np
import re
import torch
import torch.nn as nn
import torch.nn.functional as F
import argparse

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

# change a long uint number into several int64 numbers
def big_int_2_int64(number, digit):
    divisor = 0x100000000
    output = []
    for i in range(int(np.ceil(digit//32))):
        output.append(int(number % divisor))
        number = int(number // divisor)
    return output



address_type = {'ERC20':1, 'ERC721':2, 'ERC1155':3, 'Unknown':4}

w3 = prepare_web3()

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--print",  action="store_true", help="print the result", default=False)
args = parser.parse_args()

event_db = leveldb.LevelDB('db/event_db')

tx_dict = open_json("./example_poc/tx.json")
for tx_i in range(1, len(tx_dict)+1):
    addr_list, decoded_logs = process_tx(w3, tx_dict[str(tx_i)], event_db)

    fasttext.util.download_model('en', if_exists='ignore')
    fn_model = fasttext.load_model('cc.en.300.bin')
    # log
    # AttributeDict({'address': '0xdAC17F958D2ee523a2206206994597C13D831ec7', 'blockHash': HexBytes('0x39d88daafb66b3bc7553086437bc143d1bb7ddb8c7c305488aa709dfff9c19ae'),
    # 'blockNumber': 16424933, 'data': '0x0000000000000000000000000000000000000000000000000000000007270e00', 'logIndex': 76, 'removed': False,
    # 'topics': [HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'), HexBytes('0x0000000000000000000000005c65a9df43080a388071adfdd2ce2f94ad30e3b5'),
    # HexBytes('0x000000000000000000000000e9709135f4e391e240867c23b09b0a43f404e68a')],
    # 'transactionHash': HexBytes('0x015b2b4858e8be25a2fdcfb7697709a6d9f2dcb42bcc0c0dad4763e36f98e619'), 'transactionIndex': 14})

    for log_i, log in enumerate(decoded_logs):
        assert not (log == 'Unknown Event')
        # extract funtion name, function structure and parameters
        # In this step, we don't conside unbounded arrays and strings, we will deal with that later
        function_signature = log[0]     # Transfer(address,address,uint256)
        parameters = log[1]             # ['0x5c65a9df43080a388071adfdd2ce2f94ad30e3b5', '0xe9709135f4e391e240867c23b09b0a43f404e68a', 120000000]
        parameters_size = len(parameters)

        # after using some regular expression method, we get the function name and function structure from function signature
        function_name = re.findall(r'.+(?=\()', function_signature)[0]
        function_structure = re.findall(r'(?<=\().+(?=\))', function_signature)[0].split(',')

        # Before vectorize the function name, we need to build a model for function name
        # In this part, we assume that we already have a well trained model for function name
        fn_vector = fn_model.get_sentence_vector(function_name)
        # print(type(fn_vector))      # numpy.ndarray
        # print(len(fn_vector))       # 300

        # for address, we use its category
        new_parameters = []
        for i in range(parameters_size):
            if function_structure[i] == 'address':
                new_parameters.append(address_type[classify_address(w3, w3.toChecksumAddress(parameters[i]))])
                # parameters = np.array([4, 4, 120000000])
            # divide long uint into several int64
            elif re.search(r'uint', function_structure[i]) != None:
                digit = re.findall(r'(?<=uint)(\d+)', function_structure[i])
                # if the parameter type is 'uint'
                if len(digit) == 0:
                    digit = 256
                else:
                    digit = int(digit[0])
                new_parameters.extend(big_int_2_int64(parameters[i], digit))
            else:
                new_parameters.append(parameters[i])

        # put fn_vector and parameter_vector together

        # create some weight matrixs
        fn_size = np.size(fn_vector)

        v1 = torch.from_numpy(fn_vector)
        v2 = torch.LongTensor(new_parameters)

        model = LogEmbedding(fn_size, len(new_parameters))
        result = model.forward(v1, v2)
        torch.save(result, './example_poc/result/tx'+str(tx_i)+'_log'+str(log_i+1)+'.pth')
        if args.print:
            print('tx'+str(tx_i)+'_log'+str(log_i+1), ' size = ', result.size())
            print(result)
