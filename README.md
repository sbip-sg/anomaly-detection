# Anomaly-detection
Anomaly detection for transaction logs on ETH-family blockchains.
## Install dependencies and run
Should use python virtual env or anaconda
* `pip install -r requirements.txt`
* `python main.py -h`

Sample usage: 
* `python main.py -t 0x2272f93e8ce2b475521ed436cd72fca150fd6b672a867b9e6971b8c0dea5c331`
* `python main.py -a 0xdAC17F958D2ee523a2206206994597C13D831ec7`
## TODO 
* [x] Template for interacting with blockchain + getting tx info  
* [ ] Clasify given address to different classes. Using function + event signatures on ERC20, todo other ERC standards
* [ ] Find a way to decode log entries to more structured data
* [ ] Build database of decoded + cleaned tx log
## Team
* Minh
* KunPeng
* ShaoFeng
