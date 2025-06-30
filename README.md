# ETH Transaction Processing Pipelines

Anomaly detection for transaction logs on ETH-family blockchains.

This main branch is only for block level detection. If you want detection for single transaction, please switch branch.

## Install dependencies
Tested on Python 3.10, other versions may work but are not guaranteed. To use anaconda, you can create a new environment and install dependencies:

``` bash
conda create -n anomaly python=3.10
conda activate anomaly

pip install -r requirements.txt
```

This project needs a signature db to decode the events and functions. Please copy the db folder from here. https://github.com/sbip-sg/evm-signature-database. *Currently only works on Linux.*

Also, this repo is based on Foundry cast, please install related repo here. https://github.com/foundry-rs/foundry

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

The input data is block number you want to detect.

## How to process?
``` bash
python pipeline.py <blocknumber> <chain> -o (-llm)
```
It will process the hash in your file.

-llm is optional and it uses chatgpt to detect the transaction (not free-usage).

## How to collect result?

Open result folder and hash_chain folder. File basic_info.json is the basic information of the transaction.

In folder token_info, file balance.json stores balance changes of transactions and file tokenflow.json stores token transferring. The other files are storing exchange rates and token address relations. 

In folder trace_json, trace_hash.json stores raw result of the trace of this transaction. 

In folder invocation_tree, decode_trace_hash.json stores detailed result of the trace.

## Project Structure
### utils
Utility to process transaction information.
- **`utils/collect(get)_***.py`**  
  Collect corresponded information in the name 

- **`utils/db_tools.py`**  
  Tools for querying database of 4byte decoding.

- **`utils/decode_trace.py`**
  Decode and refract generated trace by Foundry.

- **`utils/generate_output.py`**  
  Generate prompts for llm. Old version is for long generation.

- **`utils/token_info.py`**  
  Collect information about token transfer from trace
 
- **`utils/tools.py`**  
  Tool functions used in other part
 
- **`utils/tx_detction.py`**  
  Process single transaction with above collecting methods.

- **`utils/chain_token_dict.json`**  
  Store hard encoded information for each blockchain.

### detect_utils
Utility to filter and detect transaction information. Have deprecated files and won't introduce here.
- **`detect_utils/rule_***.py`**  
  Rule detection for different types of attack by trace.  

- **`detect_utils/bytes_detection.py`**  
  Use to detect basic info and for first filter.

- **`detect_utils/tools.py`**  
  Tool functions used in other part
 
- **`detect_utils/detect_all.py`**  
  Process single transaction with all detection methods.

- **`detect_utils/gas_limit.json`**  
  Store gas limits of the common 4byte functions in ethereum blockchain during one year.

### llama_finetune
Not executing files in this project. Store finetuning example code. Also package requirements for them are not listed
in requirement.txt. 

Requires: datasets, transformers, tqdm, numpy, pandas, sklearn, peft, trl, torch

Recommend to run in gpu environment.

Names are usage of these Python files.

### dataset
Store collected and sampled dataset.

- **`dataset/attack_blocks.txt`**  
  List of blocks having anomaly transactions.
 
- **`dataset/sample_normal_block.txt`**  
  List of blocks sampled from attack blocks.

- **`dataset/block_atk_dict.json`**  
  Show which transactions in attack blocks are anomaly transactions