from detect_utils.tools import collect_from_file, filter_transaction, check_balance

MIN_CALL_LENGTH = 6  # the low the more false positives
assert MIN_CALL_LENGTH > 1

# Detect whether the trace contains cycling calls
def has_cycle(xs):
    n = len(xs)
    for seq_len in range(2, n // 2 + 1):
        for i in range(n - seq_len + 1):
            subsequence = tuple(xs[i:i + seq_len])
            remaining_calls = xs[i + seq_len:]

            if len(subsequence) >= MIN_CALL_LENGTH and subsequence in zip(
                    *[remaining_calls[j:] for j in range(seq_len)]):
                return subsequence

    return None


# Detector containing two checks to be considered as possible hack:
# 1. cyclic calls in transactions: each sequence of calls with minimum length MIN_CALL_LENGTH
# 2. if the sender's balance changes by more than 10k USD
def detect_cyclic_transaction(tx_hash, chain):
    basic_info = collect_from_file(tx_hash, chain, '/basic_info.json')
    if not filter_transaction(basic_info):
        return False

    sender = basic_info.get('from')

    trace = collect_from_file(tx_hash, chain, '/invocation_tree/decode_trace_' + tx_hash + '.json')
    functions = []

    for call in trace:
        if call['type'] == 'event':
            pass  # ignore event in this detectorF
        elif 'call' in call['type']:
            functions.append((call['from'], call['to'], call['function']))
        else:
            print(f"Unknown trace type: {call['type']}")

    possible_hack = False
    if has_cycle(functions) is not None:
        possible_hack = check_balance(tx_hash, chain, sender)

    return possible_hack
