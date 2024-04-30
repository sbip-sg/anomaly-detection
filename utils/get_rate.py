import ccxt
from datetime import datetime

coin_dict = {
	'WETH': 'ETH',
	'imBTC': 'BTC'
}

def to_available(timestamp):
	# Get the current timestamp
	current_timestamp = datetime.now().timestamp()

	# Calculate the difference between current timestamp and old timestamp
	time_difference = current_timestamp - timestamp

	# Check if the difference is more than 12 hours
	if time_difference > 8 * 3600:
		return timestamp
	else:
		return int(current_timestamp - 8 * 3600)

def get_rate(time_stamp, currency):
	exchange = ccxt.binance()
	if currency in coin_dict.keys():
		currency = coin_dict[currency]
	if exchange.has['fetchOHLCV']:
		try:
			# Example 'BTC/USDT'
			ohlcv = exchange.fetch_ohlcv(currency + '/USDT', '1d', since=to_available(time_stamp) * 1000, limit=1)
			exchange_rate = ohlcv[0][4]
		except Exception as e:
			exchange_rate = 0
	else:
		exchange_rate = 0

	return exchange_rate
