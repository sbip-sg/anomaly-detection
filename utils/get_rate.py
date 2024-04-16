from web3.middleware import geth_poa_middleware
import ccxt
from web3 import Web3
import datetime

def get_rate(transaction_hash, currency):
	exchange = ccxt.binance()
	w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
	w3.middleware_onion.inject(geth_poa_middleware, layer=0)
	transaction = w3.eth.get_transaction(transaction_hash)
	timestamp = w3.eth.get_block(transaction['blockNumber'])['timestamp']
	transaction_time = datetime.datetime.utcfromtimestamp(timestamp)
	if exchange.has['fetchOHLCV']:
		# Example 'BTC/USDT'
		ohlcv = exchange.fetch_ohlcv(currency + '/USDT', '1d', since=timestamp * 1000, limit=1)
		exchange_rate = ohlcv[0][4]
	else:
		print('can not find exchange rate')
		exchange_rate = 0

	return exchange_rate, transaction_time