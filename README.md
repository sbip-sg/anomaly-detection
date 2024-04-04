# ETH Transaction Processing Pipelines

Anomaly detection for transaction logs on ETH-family blockchains.

## Install dependencies

pip install -r requirements.txt

## How to set input data?

The input data is transaction hash starting with "0x".

Data structure should be like a file in which each line is a transaction hash.

## How to process?

python pipeline.py <yourfile>. It will process the hash in your file. Make sure that there is no result folder.

## How to collect result?

Open result folder. Basic_info.csv is the basic information of transactions.

Folder event_json stores json files containing raw event data. Folder decoded_eventstores json files containing decoded event data. For traces, they are similarly stored.

File balance.json stores balance changes of transactions in a dictionary. Keys are transaction hash, values are dictionary storing balance changes of each address. File othertoken.json is a intermediate product and you can delete it.

After retriving data, you need to delete reuslt folder to start another processing task.
