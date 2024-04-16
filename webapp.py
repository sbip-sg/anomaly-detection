from flask import Flask, request, jsonify, render_template, redirect, url_for

import os
import json

app = Flask(__name__)

from pipeline import main as process_request


@app.template_filter('formatjson')
def formatjson_filter(data):
    return json.dumps(data, indent=4)

def get_results(tx_hash, overwrite):
    folder_prefix = f'result/{tx_hash}_eth'
    process_request(tx_hash, overwrite)
    try:
        with open(f'{folder_prefix}/basic_info.json', 'r') as f:
            basic_info = json.load(f)
        with open(f'{folder_prefix}/balance.json', 'r') as f:
            balance_info = json.load(f)
        with open(f'{folder_prefix}/othertoken.json', 'r') as f:
            other_token_info = json.load(f)
        with open(f'{folder_prefix}/decoded_trace/trace_{tx_hash}.json', 'r') as f:
            decoded_trace = json.load(f)
        with open(f'{folder_prefix}/decoded_event/{tx_hash}_logs.json', 'r') as f:
            decoded_event = json.load(f)
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
    except Exception as e:
        return {"error": str(e)}

@app.route('/', methods=['GET', 'POST'])
def index():
    token_names = {
        "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee": "ETH",
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "Wrapped ETH"
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
    app.run(debug=True, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
