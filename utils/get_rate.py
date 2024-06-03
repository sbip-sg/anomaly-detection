from datetime import datetime
import requests
import json

currency_dict = {}

file = open("utils/token.json")
transform = json.load(file)

def collect(token, time):
    url = ('https://api.coingecko.com/api/v3/coins/' + token + '/history?date='+time+'&localization=false')

    try:
        data = requests.get(url).json()
        return data['market_data']['current_price']['usd']
    except Exception as e:
        print(f"Error: Unable to fetch data from Coingecko {e}")
        return 0

def get_rate(time_stamp, currency):
    if currency not in currency_dict.keys():
        try:
            token = transform[currency.lower()][0]
            # Convert timestamp to datetime object
            date_time = datetime.fromtimestamp(time_stamp)

            # Format datetime object to dd-mm-yyyy
            formatted_date = date_time.strftime('%d-%m-%Y')

            exchange_rate = collect(token, formatted_date)
        except Exception as e:
            print(f"Error: Unknown Token")
            exchange_rate = 0

        currency_dict[currency] = exchange_rate

    else:
        exchange_rate = currency_dict[currency]

    return exchange_rate
