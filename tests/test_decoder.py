import unittest
import os
from eth_utils import to_int, to_bytes
from main import decode_log_from_signature


class TestDecoder(unittest.TestCase):
    def test_signature_decoder_simple(self):
        inputs = decode_log_from_signature(
            "Approval(address,address,uint256)",
            [
                "0x000000000000000000000000a3718AC8dedD7d4B7163d50dAe0555b864461602",
                "0x00000000000000000000000068b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
            ],
            "0x00000000000000000000000000000000000000000000000000000000004c4b40",
        )
        print(inputs)
        # self.assertEqual(inputs[0], "0x21a31ee1afc51d94c2efccaa2092ad1028285549")
        # self.assertEqual(inputs[1], "0xfa09f6f245870b10416638c23383fd477ca1c17f")
        # self.assertEqual(inputs[2], 90280000000000000000)

    def test_signature_decoder_complex(self):

        inputs = decode_log_from_signature(
            "TransactionBatchAppended(uint256,bytes32,uint256,uint256,bytes)",
            ["0x000000000000000000000000000000000000000000000000000000000005b7d0"],
            "0x99376a1bb23ef369547a93e252b662149b11e9f495246092c50919113c19b02000000000000000000000000000000000000000000000000000000000000000f40000000000000000000000000000000000000000000000000000000003000bba00000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000000",
        )
        print(inputs)
        # TODO: assert equals all items
        # self.assertEqual(inp, 1)
