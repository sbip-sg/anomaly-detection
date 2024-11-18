from datetime import datetime
import requests
import json
import time
import os
import sys

# Record collected cryptocurrency to avoid extra requests.
currency_dict = {}


def get_resource_path(relative_path):
    """ Get absolute path to resource, works for both development and PyInstaller. """
    if getattr(sys, '_MEIPASS', False):  # Running in a PyInstaller bundle
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)


# Inputs are token symbols and coingecko api needs token's id. Collected top 300 tokens in ethereum environment.
with open(get_resource_path("utils/token.json")) as file:
    transform = json.load(file)


# Request coingecko api to get token exchange rate to usd (This function is not stable when calling too frequently)
def collect(token, date):
    # Can only get exchange rates since one year ago.
    url = ('https://api.coingecko.com/api/v3/coins/' + token + '/history?date=' + date + '&localization=false')

    try:
        data = requests.get(url).json()
        time.sleep(13)
        return data['market_data']['current_price']['usd']
    except Exception as e:
        print(f"Error: Unable to fetch data from Coingecko {e}")
        time.sleep(13)
        return 0


# Get exchange rate of cryptocurrency
# Plans:
#   1, Find more stable api
#   2, Build an exchange rate database and maintain it everyday
def get_rate(time_stamp, currency):
    if currency.lower() == 'usdc' or currency.lower() == 'usdt':
        return 1
    if currency not in currency_dict.keys():
        try:
            token = transform[currency.lower()][0]
            # Convert timestamp to datetime object
            date_time = datetime.fromtimestamp(time_stamp)

            # Format datetime object to dd-mm-yyyy
            formatted_date = date_time.strftime('%d-%m-%Y')
            exchange_rate = collect(token, formatted_date)
        except Exception as e:
            print(f"Error: Unable to fetch exchange rate of {currency}")
            exchange_rate = 0

        currency_dict[currency] = exchange_rate

    else:
        exchange_rate = currency_dict[currency]

    return exchange_rate
