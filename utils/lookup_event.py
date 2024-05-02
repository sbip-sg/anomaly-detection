import leveldb
function_db = leveldb.LevelDB('../db/event_db')


def get_event_db_signature(function_hash: str):
    """
    Get the event signature from the database with the given function hash.
    Returns None if the function hash is not found.
    Args:
        function_hash (str): 4bytes(8 hex digits) function hash, e.g. 0xa9059cbb

    Returns:
        str:  event signature
        If multiple signatures have the same hash, all signatures are returned, separated by a semicolon ";".
        e.g. "transfer(address,uint256);transferFrom(address,address,uint256)"
    """
    if function_hash.startswith('0x'):
        function_hash = function_hash[2:]
    try:
        signatures = function_db.Get(function_hash.encode()).decode()
    except KeyError:
        return None
    return signatures