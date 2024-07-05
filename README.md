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
python pipeline.py <txhash> <chain> -o
```
It will process the hash in your file. Make sure that there is no result folder.

## How to collect result?

Open result folder. Basic_info.csv is the basic information of transactions.

Folder event_json stores json files containing raw event data. Folder decoded_eventstores json files containing decoded event data. For traces, they are similarly stored.

File balance.json stores balance changes of transactions in a dictionary. Keys are transaction hash, values are dictionary storing balance changes of each address. File othertoken.json is a intermediate product and you can delete it.
