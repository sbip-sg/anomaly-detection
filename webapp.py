from flask import Flask, request, jsonify, render_template, send_from_directory, render_template
from flask_cors import CORS
import os
import json
import traceback
import werkzeug

app = Flask(__name__, static_folder='build')
CORS(app)

from pipeline import main as process_request

def try_read_as_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        traceback.print_exc()
        return None

def should_overwrite(request):
    return request.values.get('overwrite', 'false').lower() in {'on', 'true', '1', 't', 'y', 'yes'}

@app.template_filter('formatjson')
def formatjson_filter(data):
    return json.dumps(data, indent=4)

def get_results(tx_hash, chain, overwrite):
    folder_prefix = f'result/{tx_hash}_{chain}'
    endpoint_idx = 0
    while True:
        try:
            process_request(tx_hash, chain, overwrite, endpoint_idx)
            break
        except ValueError as e:
            traceback.print_exc()
            import shutil
            shutil.rmtree(folder_prefix, ignore_errors=True)
            print(f'Error processing request: {e}\n Removing dirty files... ')
            return {"error": str(e)}
        except Exception as e:
            endpoint_idx += 1
            print(f'Error processing request: {e}\n retry ... ')
    basic_info = try_read_as_json(f'{folder_prefix}/basic_info.json') or {}
    balance_info = try_read_as_json(f'{folder_prefix}/balance.json') or {}
    decoded_trace = try_read_as_json(f'{folder_prefix}/invocation_tree/decode_trace_{tx_hash}.json') or {}
    token_flow = try_read_as_json(f'{folder_prefix}/tokenflow.json') or {}
    results = {
        'basic_info': basic_info,
        'balance_info': balance_info,
        'token_flow': token_flow,
        'invocation_tree': decoded_trace
    }
    return results

@app.route('/debug', methods=['GET', 'POST'])
def debug_handler():
    chain = request.values.get('chain', 'eth')
    overwrite = should_overwrite(request)
    if request.method == 'POST':
        tx_hash = request.form.get('txhash')
        chain = request.form.get('chain')

    elif request.method == 'GET':
        tx_hash = request.args.get('txhash')
        chain = request.form.get('chain')


    results = get_results(tx_hash, chain, overwrite) if tx_hash else {}

    return render_template('index.html', results=results)


@app.route('/process', methods=['GET'])
def process_handler():
    chain = request.values.get('chain', 'eth')
    tx_hash = request.args.get('txhash')
    overwrite = should_overwrite(request)
    if not tx_hash:
        return jsonify({"error": "Transaction hash is required"}), 400

    results = get_results(tx_hash, chain, overwrite)
    if "error" in results:
        return jsonify(results), 500
    return jsonify(results)

@app.route('/')
def index_handler():
    return send_from_directory('build', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    try:
        return send_from_directory('build', filename)
    except werkzeug.exceptions.NotFound:
        return send_from_directory('build', 'index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
