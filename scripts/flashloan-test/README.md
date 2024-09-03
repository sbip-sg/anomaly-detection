### Detection Process

Necessary Data: Traces and Balances(Only bool as flow in and out is needed)

1. getflashloantraces:

Go through all traces. Select all traces with name.lower() as flashloan.

2. receiverlist:

For each trace, get parameters (address) named with recipient, receiver or to. When it is a list, choose the first one as an address.

3. balancelist:

For each receiver address, get its balance changes of all assets.

4. detect transactions:

With addresses and balancelists, see whether the address has a balancelist with all types of assets flowing in. If so, the possibility of that address is in an attack transaction will be higher. After looking up all addresses in a transaction, see the possible address occupies how much in the whole address list. If possibility > 0.5, it is an attack.
