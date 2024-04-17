import ccxt

coin_dict = {
	'WETH': 'ETH',
	'imBTC': 'BTC'
}


def get_rate(time_stamp, currency):
	exchange = ccxt.binance()
	if currency in coin_dict.keys():
		currency = coin_dict[currency]
	if exchange.has['fetchOHLCV']:
		try:
			# Example 'BTC/USDT'
			ohlcv = exchange.fetch_ohlcv(currency + '/USDT', '1d', since=time_stamp * 1000, limit=1)
			exchange_rate = ohlcv[0][4]
		except Exception as e:
			exchange_rate = 0
	else:
		exchange_rate = 0

	return exchange_rate
