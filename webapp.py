from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)

from pipeline import main as process_request

def try_read_as_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


@app.template_filter('formatjson')
def formatjson_filter(data):
    return json.dumps(data, indent=4)

def get_results(tx_hash, overwrite):
    folder_prefix = f'result/{tx_hash}_eth'
    process_request(tx_hash, overwrite)
    basic_info = try_read_as_json(f'{folder_prefix}/basic_info.json') or {}
    balance_info = try_read_as_json(f'{folder_prefix}/balance.json') or {}
    other_token_info = try_read_as_json(f'{folder_prefix}/othertoken.json') or {}
    decoded_trace = try_read_as_json(f'{folder_prefix}/decoded_trace/trace_{tx_hash}.json') or {}
    decoded_event = try_read_as_json(f'{folder_prefix}/decoded_event/{tx_hash}_logs.json') or {}
    results = {
        'basic_info': basic_info,
        'balance_info': balance_info,
        'other_token_info': other_token_info,
        'other_data' : {
            'decoded_trace': decoded_trace,
            'decoded_event': decoded_event,
        }
    }
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    token_names = {
        "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee": "ETH",
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "Wrapped ETH",
        "0xdac17f958d2ee523a2206206994597c13d831ec7": "Tether: USDT Stablecoin",
        "0xb8c77482e45f1f44de1745f52c74426c631bdd52": "BNB",
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC",
        "0xae7ab96520de3a18e5e111b5eaab095312d7fe84": "stETH",
        "0x582d872a1b094fc48f5de31d3b73f2d9be47def1": "Wrapped TON Coin",
        "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce": "SHIBA INU",
        "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": "Wrapped BTC",
        "0x50327c6c5a14dcade707abad2e27eb517df87ab5": "TRON",
        "0x514910771af9ca656af840dff83e8264ecf986ca": "ChainLink Token",
        "0x85f17cf997934a597031b2e18a9ab6ebd4B9f6a4": "NEAR"

    }

    if request.method == 'POST':
        tx_hash = request.form.get('txhash')
        overwrite = request.form.get('overwrite', 'false').lower() in ['true', '1', 't', 'y', 'yes']
    elif request.method == 'GET':
        tx_hash = request.args.get('txhash')
        overwrite = request.args.get('overwrite', 'false').lower() in ['true', '1', 't', 'y', 'yes']

    results = get_results(tx_hash, overwrite) if tx_hash else {}

    return render_template('index.html', results=results, token_names=token_names)


@app.route('/process', methods=['GET'])
def process():
    tx_hash = request.args.get('txhash')
    overwrite = request.args.get('overwrite', 'false').lower() in ['true', '1', 't', 'y', 'yes']
    if not tx_hash:
        return jsonify({"error": "Transaction hash is required"}), 400

    results = get_results(tx_hash, overwrite)
    if "error" in results:
        return jsonify(results), 500
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))
