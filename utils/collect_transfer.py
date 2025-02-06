# Build a function to inject information to a summary dict
def update_summary(summary, address, currency, amount):
    # if new address
    if address not in summary:
        summary[address] = {}

    # if new currency
    if currency not in summary[address]:
        summary[address][currency] = 0

    # calculate changes
    summary[address][currency] += amount
    return summary


# Function to handle other-token transfer transactions
def othertransfer(summary, currency, from_address, to_address, amount, flow):
    # Delete from from-address
    summary = update_summary(summary, from_address, currency, -amount)
    # Add to to-address
    summary = update_summary(summary, to_address, currency, amount)
    # Input transfer to dataframe flow
    if amount != 0:
        flow.loc[len(flow)] = [from_address, to_address, currency, amount]

    return summary


# Function to deal with local-token transfer transactions
def deal_transfer(summary, currency, trace, flow):
    from_address = trace["from"]
    to_address = trace["to"]
    amount = trace["value"] / 1e18

    summary = update_summary(summary, from_address, currency, -amount)
    summary = update_summary(summary, to_address, currency, amount)
    if amount != 0:
        flow.loc[len(flow)] = [from_address, to_address, currency, amount]

    return summary


# This function is from observation and would be less reliable
# Function to find the address and amount from an event
def find_address_transfer_event(trace, input):
    # from address is normally the first of the inputs
    if (trace['address'] == '0x82af49447d8a07e3bd95bd0d56f35241523fbab1' and
            input[0] == '0x0000000000000000000000000000000000000000'):
        from_address = trace['address']
    else:
        from_address = input[0]

    # If an event have more than 2 inputs, the second would be to address and the third would be amount
    if len(input) > 2:
        to_address = input[1]
        amount = input[2]

    # If an event have 2 inputs and have data, amount is normally data and the second input would be to address
    elif len(input) == 2 and trace['data']:
        amount = trace['data'][0]
        to_address = input[1]
    elif len(input) == 2:
        from_address = '0x' + '0' * 40
        to_address = input[0]
        amount = 1
    # If an event have less than 2 inputs and have data, this transfer may be from null.
    elif trace['data']:
        amount = trace['data'][0]
        from_address = trace['address']
        to_address = input[0]

    # if have no information, ignore it.
    else:
        amount = 0
        to_address = '0x' + '0' * 40
    return from_address, to_address, amount