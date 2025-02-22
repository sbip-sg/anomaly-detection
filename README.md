# ETH Transaction Processing Pipelines

Anomaly detection for transaction logs on ETH-family blockchains.

## Install dependencies
Tested on Python 3.10, other versions may work but are not guaranteed. To use anaconda, you can create a new environment and install dependencies:

``` bash
conda create -n anomaly python=3.10
conda activate anomaly

pip install -r requirements.txt
```

This project needs a signature db to decode the events and functions. Please copy the db folder from here. https://github.com/sbip-sg/evm-signature-database. *Currently only works on Linux.*

## Start backend server

``` bash
# Copy and edit the env file
cp env-example .env
python webapp.py
```

## Turnstile configuration

Configure the following to make the turnstile work properly.

From the CloudFlare dashboard:

- allowed domain(s): https://developers.cloudflare.com/turnstile/concepts/domain-management/
- Widge mode is set to `Invisible`
- Get the siteKey and secret


Set the following,

- `siteKey` in the frontend
- `secret` in the backend, to be used for validating the request


## How to set input data?

The input data is transaction hash starting with "0x".

## How to process?
``` bash
python pipeline.py <txhash> <chain> -o (-llm)
```
It will process the hash in your file.

-llm is optional and it uses chatgpt to detect the transaction (not free-usage).

## How to collect result?

Open result folder and hash_chain folder. File basic_info.json is the basic information of the transaction.

In folder token_info, file balance.json stores balance changes of transactions and file tokenflow.json stores token transferring. The other two files are storing exchange rates and token address relations. 

In folder trace_json, trace_hash.json stores raw result of the trace of this transaction. 

In folder invocation_tree, decode_trace_hash.json stores detailed result of the trace.
