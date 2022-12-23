import unittest
import os
from main import prepare_web3
from utils.address_utils import classify_address


class TestClassifier(unittest.TestCase):
    def test_erc20_classifier(self):
        w3 = prepare_web3()
        top50_dict = {5: '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84', 23: '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9',
                      24: '0x0000000000085d4780B73119b644AE5ecd22b376', 33: '0xFd09Cf7cFffa9932e33668311C4777Cb9db3c9Be', 38: '0x68749665FF8D2d112Fa859AA293F07A622782F38'}
        for address in top50_dict.values():
            self.assertEqual(classify_address(w3, address), "ERC20" )

    def test_erc721_classifier(self):
        ...
