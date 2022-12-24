import unittest
import os
from main import prepare_web3, open_json
from utils.address_utils import classify_address


class TestClassifier(unittest.TestCase):
    def test_erc20_classifier(self):
        w3 = prepare_web3()
        top100_dict = open_json('top100.json')
        for address in top100_dict.values():
            self.assertEqual(classify_address(w3, address), "ERC20" )

    # def test_erc721_classifier(self):
    #     ...