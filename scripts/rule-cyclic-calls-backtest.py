import argparse
from web3 import Web3
import os
import json
from datetime import datetime
import time
import requests
from itertools import chain

# These are the transactions that are known to be hacks, taken from the tx hashs at
# https://github.com/sbip-sg/anomaly-detection/blob/Dataset/Decoding/attact_dataset/traces.json
real_hacks_txs = ['0x00b375f8e90fc54c1345b33c686977ebec26877e2c8cac165429927a6c9bdbec',
                  '0x00edd68087ee372a1b6e05249cc6c992bb7b8478cc0ddc70c2a1453428285808',
                  '0x03543ef96c26d6c79ff6c24219c686ae6d0eb5453b322e54d3b6a5ce456385e5',
                  '0x04b166e7b4ab5105a8e9c85f08f6346de1c66368687215b0e0b58d6e5002bc32',
                  '0x04e16a79ff928db2fa88619cdd045cdfc7979a61d836c9c9e585b3d6f6d8bc31',
                  '0x055cec4fa4614836e54ea2e5cd3d14247ff3d61b85aa2a41f8cc876d131e0328',
                  '0x07887fffc4488354d813fdcca5da0586dd6f9a3da36d503af768302eacbeec41',
                  '0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb',
                  '0x0af5a6d2d8b49f68dcfd4599a0e767450e76e08a5aeba9b3d534a604d308e60b',
                  '0x0ec3f2488a93839524add10ea229e773f6bc891b4eb4794c3337d4495263790b',
                  '0x0fe2542079644e107cbf13690eb9c2c65963ccb79089ff96bfaf8dced2331c92',
                  '0x125581f9551c0ae1098e132823cd5cffc0c942be4e6fed6cd447bde017e87130',
                  '0x1274b32d4dfacd2703ad032e8bd669a83f012dde9d27ed92e4e7da0387adafe4',
                  '0x138daa4cbeaa3db42eefcec26e234fc2c89a4aa17d6b1870fc460b2856fd11a6',
                  '0x160c5950a01b88953648ba90ec0a29b0c5383e055d35a7835d905c53a3dda01e',
                  '0x1655592eda3ebbba7c530ab3327daeae95fa95d05c3dec40338471245da10cfe',
                  '0x171072422efb5cd461546bfe986017d9b5aa427ff1c07ebe8acc064b13a7b7be',
                  '0x1a7ee0a7efc70ed7429edef069a1dd001fbff378748d91f17ab1876dc6d10392',
                  '0x1f1aba5bef04b7026ae3cb1cb77987071a8aff9592e785dd99860566ccad83d1',
                  '0x1fe5a53405d00ce2f3e15b214c7486c69cbc5bf165cf9596e86f797f62e81914',
                  '0x21e9d20b57f6ae60dac23466c8395d47f42dc24628e5a31f224567a2b4effa88',
                  '0x23fb7f093e827ed061aafb574cfd420eab879621c7f78cb341292e106a3a88c0',
                  '0x264e16f4862d182a6a0b74977df28a85747b6f237b5e229c9a5bbacdf499ccb4',
                  '0x26a83db7e28838dd9fee6fb7314ae58dcc6aee9a20bf224c386ff5e80f7e4cf2',
                  '0x27981c7289c372e601c9475e5b5466310be18ed10b59d1ac840145f6e7804c97',
                  '0x2881e839d4d562fad5356183e4f6a9d427ba6f475614ce8ef64dbfe557a4a2cc',
                  '0x2a027c8b915c3737942f512fc5d26fd15752d0332353b3059de771a35a606c2d',
                  '0x2c9f87e285026601a2c8903cf5f10e5b3655fbd0264490c41514ce073c42a9c3',
                  '0x2e7dc8b2fb7e25fd00ed9565dcc0ad4546363171d5e00f196d48103983ae477c',
                  '0x322592750691798488006a26aa042b55ab9d7637f9b0adc42089a4c480e51870',
                  '0x325999373f1aae98db2d89662ff1afbe0c842736f7564d16a7b52bf5c777d3a4',
                  '0x32c83905db61047834f29385ff8ce8cb6f3d24f97e24e6101d8301619efee96e',
                  '0x33f6adf410bbd0ae08b0cd44410de1e5b28e516434567113982fcac36ed9e1a4',
                  '0x35ecf595864400696853c53edf3e3d60096639b6071cadea6076c9c6ceb921c1',
                  '0x366df0c20e00666749b16ae00475b3c41834dc659ebb29e059aa9bffa892c038',
                  '0x37acd17a80a5f95728459bfea85cb2e1f64b4c75cf4a4c8dcb61964e26860882',
                  '0x37cb8626e45f0749296ef080acb218e5ccc7efb2ae4d39c952566dc378ca1c4c',
                  '0x3b19e152943f31fe0830b67315ddc89be9a066dc89174256e17bc8c2d35b5af8',
                  '0x3c09c6306b67737227edc24c663462d870e7c2bf39e9ab66877a980c900dd5d5',
                  '0x3d163bfbec5686d428a6d43e45e2626a220cc4fcfac7620c620b82c1f2537c78',
                  '0x3e9bcee951cdad84805e0c82d2a1e982e71f2ec301a1cbd344c832e0acaee813',
                  '0x3ed75df83d907412af874b7998d911fdf990704da87c2b1a8cf95ca5d21504cf',
                  '0x4227bca8ed4b8915c7eec0e14ad3748a88c4371d4176e716e8007249b9980dc9',
                  '0x422e7b0a449deba30bfe922b5c34282efbdbf860205ff04b14fd8129c5b91433',
                  '0x44aad3b853866468161735496a5d9cc961ce5aa872924c5d78673076b1cd95aa',
                  '0x4ab68b21799828a57ea99c1288036889b39bf85785240576e697ebff524b3930',
                  '0x4b3df6e9c68ae482c71a02832f7f599ff58ff877ec05fed0abd95b31d2d7d912',
                  '0x4bb10927ea7afc2336033574b74ebd6f73ef35ac0db1bb96229627c9d77555a0',
                  '0x4f4d6909a442b4d86f79a9044dcada6a128ddd9f62c26f410134a72d2fc31389',
                  '0x51ce3d9cfc85c1f6a532b908bb2debb16c7569eb8b76effe614016aac6635f65',
                  '0x53835af1b7df33435188d2380328b81c0e8a22b01353c76e3dac352275895b45',
                  '0x53eeab4447db331dbb47f93fd58a95d6faa230d559acde0687f8b5f5829e7a45',
                  '0x578a195e05f04b19fd8af6358dc6407aa1add87c3167f053beb990d6b4735f26',
                  '0x59faab5a1911618064f1ffa1e4649d85c99cfd9f0d64dcebbc1af7d7630da98b',
                  '0x5bbab18059f8c3fec56a0ddcd15feddf7cda8b8007b254436956db1d9ffe72ec',
                  '0x5c5688a9f981a07ed509481352f12f22a4bd7cea46a932c6d6bbe67cca3c54be',
                  '0x6189ad07894507d15c5dff83f547294e72f18561dc5662a8113f7eb932a5b079',
                  '0x6200bf5c43c214caa1177c3676293442059b4f39eb5dbae6cfd4e6ad16305668',
                  '0x6233c9315dd3b6a6fcc7d653f4dca6c263e684a76b4ad3d93595e3b8e8714d34',
                  '0x674f74b30a3d7bdf15fa60a7c29d96a402ea894a055f624164a8009df98386a0',
                  '0x6899b8caee16dbd75359cabcd24e32b2362c474cdf39ea810cf4386018761beb',
                  '0x68cdec0ac76454c3b0f7af0b8a3895db00adf6daaf3b50a99716858c4fa54c6f',
                  '0x69272d8c84d67d1da2f6425b339192fa472898dce936f24818fda415c1c1ff3f',
                  '0x6bfd9e286e37061ed279e4f139fbc03c8bd707a2cdd15f7260549052cbba79b7',
                  '0x6cba3a67d6b8de664d860b096c8c558a1d65e5fa9735c657ddc98f67969561a2',
                  '0x6e6e556a5685980317cb2afdb628ed4a845b3cbd1c98bdaffd0561cb2c4790fa',
                  '0x708ffcf4a76bd159056afb17ce6c5f5adcb5899e465bbf038aae79c3cef666ae',
                  '0x726459a46839c915ee2fb3d8de7f986e3c7391c605b7a622112161a84c7384d0',
                  '0x7ac4a98599596adbf12fffa2bd23e2a2d2ac7e8989b6ea043fcc412a29126555',
                  '0x7cefbfd14497b1c577423d94ea521615991eee2590fab980230d9dd1d80ccf1c',
                  '0x7d2296bcb936aa5e2397ddf8ccba59f54a178c3901666b49291d880369dbcf31',
                  '0x800a5b3178f680feebb81af69bd3dff791b886d4ce31615e601f2bb1f543bb2e',
                  '0x8037b3dc0bf9d5d396c10506824096afb8125ea96ada011d35faa89fa3893aea',
                  '0x804ff3801542bff435a5d733f4d8a93a535d73d0de0f843fd979756a7eab26af',
                  '0x81e9918e248d14d78ff7b697355fd9f456c6d7881486ed14fdfb69db16631154',
                  '0x82fc23992c7433fffad0e28a1b8d11211dc4377de83e88088d79f24f4a3f28b3',
                  '0x84156ea5360b679dfa7cdda80c16aafbfdf1ba20b84bcf76f79666f0c405b86f',
                  '0x873f7c77d5489c1990f701e9bb312c103c5ebcdcf0a472db726730814bfd55f3',
                  '0x8a8145ab28b5d2a2e61d74c02c12350731f479b3175893de2014124f998bff32',
                  '0x8af9b5fb3e2e3df8659ffb2e0f0c1f4c90d5a80f4f6fccef143b823ce673fb60',
                  '0x8b74995d1d61d3d7547575649136b8765acb22882960f0636941c44ec7bbe146',
                  '0x8bcac5e570aa695b5e0ce7dd58766eaa5830f44bbef5008aef63c6efb036e717',
                  '0x8c3f442fc6d640a6ff3ea0b12be64f1d4609ea94edd2966f42c01cd9bdcf04b5',
                  '0x8d3036371ccf27579d3cb3d4b4b71e99334cae8d7e8088247517ec640c7a59a5',
                  '0x8d8404d056607815c04dd286858da123c6e6aea29a1197e21a803fa67ebedd7c',
                  '0x8e1b0ab098c4cc5f632e00b0842b5f825bbd15ded796d4a59880bb724f6c5372',
                  '0x906d06acd236c48a8c8708d7dc50d968b8faad7c7c393e7c01549adf4922b180',
                  '0x90b468608fbcc7faef46502b198471311baca3baab49242a4a85b73d4924379b',
                  '0x914c1ae4f03657064f0b1d5ddc6e06f39e82bce6fb2f726efdca52c092fbfc26',
                  '0x927b784148b60d5233e57287671cdf67d38e3e69e5b6d0ecacc7c1aeaa98985b',
                  '0x93a033917fcdbd5fe8ae24e9fe22f002949cba2f621a1c43a54f6519479caceb',
                  '0x9437dde6c06a20f6d56f69b07f43d5fb918e6c57c97e1fc25a4162c693f578aa',
                  '0x96bf6bd14a81cf19939c0b966389daed778c3a9528a6c5dd7a4d980dec966388',
                  '0x97201900198d0054a2f7a914f5625591feb6a18e7fc6bb4f0c964b967a6c15f6',
                  '0x98d8237027797a51b1251aa239d1a85b7a209d15c9f7895b44b4ee7ee0c754fb',
                  '0x995e880635f4a7462a420a58527023f946710167ea4c6c093d7d193062a33b01',
                  '0x9a036058afb58169bfa91a826f5fcf4c0a376e650960669361d61bef99205f35',
                  '0x9a97d85642f956ad7a6b852cf7bed6f9669e2c2815f3279855acf7f1328e7d46',
                  '0x9d1351ca4ede8b36ca9cd9f9c46e3b08890d13d94dfd3074d9bb66bbcc2629b1',
                  '0x9d6d355db13361c0862f7d51913d7d31ea724dc25228782ea052f955a1d5b79d',
                  '0x9fac5412eb42aab07dcb2c5fbb03669aaa98d9c57849d44d8291d3156d9f4871',
                  '0xa02c180149ce03d1b6e3d412585000b968b7db59a277717ec51d0899c1a3c017',
                  '0xa329b27fbe0f7b7f92060a9e5370fdf03d60e5c4835f09d7234e5bbecf417ccf',
                  '0xa5fe9d044e4f3e5aa5bc4c0709333cd2190cba0f4e7f16bcf73f49f83e4a5460',
                  '0xa685928b5102349a5cc50527fec2e03cb136c233505471bdd4363d0ab077a69a',
                  '0xa6f63fcb6bec8818864d96a5b1bb19e8bd85ee37b2cc916412e720988440b2aa',
                  '0xa84aa065ce61dbb1eb50ab6ae67fc31a9da50dd2c74eefd561661bfce2f1620c',
                  '0xa9948c8f0500a867091a090d12125f88868ac29e52af6391569094e82d416904',
                  '0xaaa197c7478063eb1124c8d8b03016fe080e6ec4c4f4a4e6d7f09022084e3390',
                  '0xabfcfaf3620bbb2d41a3ffea6e31e93b9b5f61c061b9cfc5a53c74ebe890294d',
                  '0xad818ec910def08c70ac519ab0fffa084b4178014a91cd8aa2f882d972a511c1',
                  '0xad89ff16fd1ebe3a0a7cf4ed282302c06626c1af33221ebe0d3a470aba4a660f',
                  '0xadbe5cf9269a001d50990d0c29075b402bcc3a0b0f3258821881621b787b35c6',
                  '0xaf46a42fe1ed7193b25c523723dc047c7500e50a00ecb7bbb822d665adb3e1f3',
                  '0xb2e3ea72d353da43a2ac9a8f1670fd16463ab370e563b9b5b26119b2601277ce',
                  '0xb36486f032a450782d5d2fac118ea90a6d3b08cac3409d949c59b43bcd6dbb8f',
                  '0xb3af75f703ddc5d15ff872585b7d970c5204b90399a5859ec39e736a2ffbf375',
                  '0xb613c68b00c532fe9b28a50a91c021d61a98d907d0217ab9b44cd8d6ae441d9f',
                  '0xb676d789bb8b66a08105c844a49c2bcffb400e5c1cfabd4bc30cca4bff3c9801',
                  '0xbc08860cd0a08289c41033bdc84b2bb2b0c54a51ceae59620ed9904384287a38',
                  '0xbd72bccec6dd824f8cac5d9a3a2364794c9272d7f7348d074b580e3c6e44312e',
                  '0xc087fbd68b9349b71838982e789e204454bfd00eebf9c8e101574376eb990d92',
                  '0xc10ec615e2d18c8a7dad2bb2418c422472565d9622ed851298fc848c3a451387',
                  '0xc18ec2eb7d41638d9982281e766945d0428aaeda6211b4ccb6626ea7cff31f4a',
                  '0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d',
                  '0xc42fc0e22a0f60cc299be80eb0c0ddce83c21c14a3dddd8430628011c3e20d6b',
                  '0xc42fe1ce2516e125a386d198703b2422aa0190b25ef6a7b0a1d3c6f5d199ffad',
                  '0xc49499325cb5ad3bf4391ae95855ce2ee2b0222f9282c524daa1c4586a8fcd8b',
                  '0xc6c3331fa8c2d30e1ef208424c08c039a89e510df2fb6ae31e5aa40722e28fd6',
                  '0xca53e107a9a21d8f431614570a98c4718cca7172415e3fbed8842d426ac3ab54',
                  '0xcb0ad9da33ecabf75df0a24aabf8a4517e4a7c5b1b2f11fee3b6a1ad9299a282',
                  '0xcbe521aea28911fe9983030748028e12541e347b8b6b974d026fa5065c22f0cf',
                  '0xcdd93e37ba2991ce02d8ca07bf6563bf5cd5ae801cbbce3dd0babb22e30b2dbe',
                  '0xce0935010baf445e300d4d600caac7fc1fecb5ccb092cdbef57904aa7e5408b2',
                  '0xced7ca813081fb594181469001a6aff629c5874bd672cca44075d3ec768db664',
                  '0xcfe1d2b333e1b9da5e2d5f1d7697b628c818cc41f9f3020187d4ce2c2610a05c',
                  '0xcff84cc137c92e427f720ca1f2b36fbad793f34ec5117eed127060686e6797b1',
                  '0xd493c73397952049644c531309df3dd4134bf3db1e64eb6f0b68b016ee0bffde',
                  '0xd4fafa1261f6e4f9c8543228a67caf9d02811e4ad3058a2714323964a8db61f6',
                  '0xd55e43c1602b28d4fd4667ee445d570c8f298f5401cf04e62ec329759ecda95d',
                  '0xd5b4d68432cbbd912130bbb5b93399031ddbb400d8f723c78050574de7533106',
                  '0xd7ec3046ec75efbd04b3eea8752a8a6373a92c0dd813d08b655661054d3239c5',
                  '0xd9156f507c701a09d3312e1987383c7c882df50b3127e1adfd74d74052642114',
                  '0xdaccbc437cb07427394704fbcc8366589ffccf974ec6524f3483844b043f31d5',
                  '0xdd7dd68cd879d07cfc2cb74606baa2a5bf18df0e3bda9f6b43f904f4f7bbdfc1',
                  '0xddd1048fe3f2df1fb98e534a97173b32a9fca662dbd257a72725482431d3f25e',
                  '0xe0b0c2672b760bef4e2851e91c69c8c0ad135c6987bbf1f43f5846d89e691428',
                  '0xe0bada18fdc56dec125c31b1636490f85ba66016318060a066ed7050ff7271f9',
                  '0xe1f375a47172b5612d96496a4599247049f07c9a7d518929fbe296b0c281e04d',
                  '0xe28ca1f43036f4768776805fb50906f8172f75eba3bf1d9866bcd64361fda834',
                  '0xe3f0d14cfb6076cabdc9057001c3fafe28767a192e88005bc37bd7d385a1116a',
                  '0xe60c5a3154094828065049121e244dfd362606c2a5390d40715ba54699ba9da6',
                  '0xe72d4e7ba9b5af0cf2a8cfb1e30fd9f388df0ab3da79790be842bfbed11087b0',
                  '0xeaef2831d4d6bca04e4e9035613be637ae3b0034977673c1c2f10903926f29c0',
                  '0xeb87ebc0a18aca7d2a9ffcabf61aa69c9e8d3c6efade9e2303f8857717fb9eb7',
                  '0xeb8c3bebed11e2e4fcd30cbfc2fb3c55c4ca166003c7f7d319e78eaab9747098',
                  '0xec7523660f8b66d9e4a5931d97ad8b30acc679c973b20038ba4c15d4336b393d',
                  '0xec8f6d8e114caf8425736e0a3d5be2f93bbea6c01a50a7eeb3d61d2634927b40',
                  '0xecdd111a60debfadc6533de30fb7f55dc5ceed01dfadd30e4a7ebdb416d2f6b6',
                  '0xed26708a7335116bdb0673f32ace7c2f329fe3cd349e200447210f1721f335f0',
                  '0xedc214a62ff6fd764200ddaa8ceae54f842279eadab80900be5f29d0b75212df',
                  '0xede72a74d8398875b42d92c550539d72c830d3c3271a7641ee1843dc105de59e',
                  '0xede874f9a4333a26e97d3be9d1951e6a3c2a8861e4e301787093cfb1293d4756',
                  '0xefc4ac015069fdf9946997be0459db44c0491221159220be782454c32ec2d651',
                  '0xf0a13b445674094c455de9e947a25bade75cac9f5176695fca418898ea25742f',
                  '0xf1c1066c259672396b8f242311a9f1c83bfa52c27529d713d80a3da93047c37f',
                  '0xf4a3d0e01bbca6c114954d4a49503fc94dfdbc864bded5530b51a207640d86b5',
                  '0xf4ae22177c3abbb0f21defe51dd14eff68eb1b0c52ac4104186220138e8e5bb2',
                  '0xf72f1d10fc6923f87279ce6c0aef46e372c6652a696f280b0465a301a92f2e26',
                  '0xf7c21600452939a81b599017ee24ee0dfd92aaaccd0a55d02819a7658a6ef635',
                  '0xfa97c3476aa8aeac662dae0cc3f0d3da48472ff4e7c55d0e305901ec37a2f704',
                  '0xfb9942a119c45adab3980639cd829e57b41449e3b82d610892da4bb921e81d9c',
                  '0xfde10ad92566f369b23ed5135289630b7a6453887c77088794552c2a3d1ce8b7',
                  '0xfeedbf51b4e2338e38171f6e19501327294ab1907ab44cfd2d7e7336c975ace7',
                  '0xfefd829e246002a8fd061eede7501bccb6e244a9aacea0ebceaecef5d877a984',
                  '0xff1f352912666796d5cd51b5dfa3e6319544aeb5938e1e9f310fd5fcb02be6da',
                  '0xffb4bd29825bdd41adf344028f759692021cbadc2d4cb5b587e68fd8285c5eb1']

# proxies = {
#     'http': 'socks5h://localhost:9050',
#     'https': 'socks5h://localhost:9050'
# }

proxies = None


MIN_CALL_LENGTH = 6 # the low the more false positives
assert MIN_CALL_LENGTH > 1

api_trace_uri  = '/api/v1/onchain/tx/trace'
api_balance_change = '/api/v1/onchain/tx/balance-change'
api_address_label = '/v1/onchain/tx/address-label'
api_state_change = '/api/v1/onchain/tx/state-change'
api_profile = '/api/v1/onchain/tx/profile'

seen = set()

parser = argparse.ArgumentParser()
parser.add_argument('--web3-provider-url', type=str, help='Web3 provider url', required=True)
args = parser.parse_args()

WEB3_PROVIDER_URL = args.web3_provider_url


w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
block_filter = w3.eth.filter('latest')




def filter_transaction(transaction):
    # txhash = transaction['hash'].hex()
    gas_used = transaction.get('gas')
    # gas_price = transaction.get('gasPrice')
    # max_priority_fee = transaction.get('maxPriorityFeePerGas', 0)
    # base_fee = block.baseFeePerGas
    base_gas = 21000

    if gas_used > base_gas * 10: # high tips
        return transaction

    if transaction.get('to') is None:
        # contract creation, assuming nobody hacks here
        if gas_used > base_gas * 50: # TODO update this threshold if necessary
            return transaction

    if gas_used > base_gas * 100: # TODO update this threshold if necessary
        return transaction

    return None

def fetch_phalcon_data(txhash, uri, chain_id=1, data=None, timeout=10):
    url = f'https://app.blocksec.com{uri}'

    headers = {
        'accept': 'application/json',
        'accept-language': 'en;q=0.9',
        'content-type': 'application/json;charset=utf-8',
        'origin': 'https://app.blocksec.com',
        'referer': 'https://app.blocksec.com',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Brave";v="126"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }

    data = data or {
        "chainID": chain_id,
        "txnHash": txhash,
        "blocked": False
    }

    response = requests.post(url, headers=headers, json=data, timeout=timeout, proxies=proxies)
    response.raise_for_status()
    return response.json()


def has_cycle(xs):
    n = len(xs)
    for seq_len in range(2, n // 2 + 1):
        for i in range(n - seq_len + 1):
            subsequence = tuple(xs[i:i + seq_len])
            remaining_calls = xs[i + seq_len:]

            if len(subsequence) >= MIN_CALL_LENGTH and subsequence in zip(*[remaining_calls[j:] for j in range(seq_len)]):
                return subsequence

    return None

# Detector containing two checks to be considered as possible hack:
# 1. cyclic calls in transactions: each sequence of calls with minimum length MIN_CALL_LENGTH
# 2. if the sender's balance changes by more than 10k USD
def detect_transaction(transaction):
    if transaction is None:
        return None
    txhash = transaction['hash'].hex()
    sender = transaction['from'].lower()

    trace = fetch_phalcon_data(txhash, api_trace_uri)

    data_map = trace['dataMap']
    ids = [int(id) for id in data_map.keys()]
    ids = sorted(ids)
    functions = []



    for id in ids:
        t = trace['dataMap'][str(id)]
        if 'event' in t:
            pass # ignore event in this detector
        elif 'invocation' in t:
            f = t['invocation']
            functions.append((f['fromAddress'], f['address'] , f['selector']))
        else:
            print(f"Unknown trace type: {t}")

    possible_hack = False
    if has_cycle(functions) is not None:
        balance_change = fetch_phalcon_data(txhash, api_balance_change)

        sender_balance_change = [c['assets'] for c in balance_change['balanceChanges'] if c['account'] == sender]
        sender_balance_change = list(chain.from_iterable(sender_balance_change)) # flatten
        sender_usd_change = sum([(1 if c['sign'] else -1) * float(c['value'].replace(',','') or 0) for c in sender_balance_change]) # ignores asset with unknown values
        possible_hack = sender_usd_change > 10000 # 10k USD


    if possible_hack:
        print(f'Detected: {txhash}')

    return  possible_hack

def handle_transactions(transactions):
    detected = []
    failed = []
    for (txhash, transaction) in transactions:
        try:
            if detect_transaction(filter_transaction(transaction)):
                detected.append(txhash)
        except KeyboardInterrupt:
            break
        except Exception as e:
            import traceback, sys
            traceback.print_exc(file=sys.stdout)
            failed.append(txhash)
            continue
    return (detected, failed)


print('Loading transactions ...')
transactions = [(txhash, w3.eth.get_transaction(txhash)) for txhash in real_hacks_txs]

print('Processing transactions ...')
detected, failed = handle_transactions(transactions)

print(f'Total realhack transactions: {len(transactions)}')
print(f'Detected transactions: {len(detected)}' )
print(f'Failed to process: {len(failed)}' )

with open('realhacks_detected.txt', 'w') as f:
    for txhash in list(detected):
        f.write(txhash + "\n")


with open('realhacks_failed_to_process.txt', 'w') as f:
    for txhash in list(failed):
        f.write(txhash + "\n")
