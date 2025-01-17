import plyvel
import os
import csv
import pandas as pd

db_path = os.environ.get('EVENT_DB_PATH')
event_db = None
function_db = None


def get_event_db():
    global event_db
    if event_db is None:
        event_db = plyvel.DB(f'{db_path}/db/event_db')
    return event_db

def get_function_db():
    global function_db
    if function_db is None:
        function_db = plyvel.DB(f'{db_path}/db/function_db')
    return function_db


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
        signatures = get_event_db().get(function_hash.encode())
        if signatures:
            return signatures.decode()
        else:
            print(f'Error: event {function_hash} not in database')
            return None
    except KeyError:
        print(f'Error: event {function_hash} not in database')
        return None


def get_function_signature(function_hash: str):
    """
    Get the function signature from the database with the given function hash.
    Returns None if the function hash is not found.
    Args:
        function_hash (str): 4bytes(8 hex digits) function hash, e.g. 0xa9059cbb

    Returns:
        str: function signature, e.g. "transfer(address,uint256)".
        If multiple signatures have the same hash, all signatures are returned, separated by a semicolon ";".
        e.g. "transfer(address,uint256);transferFrom(address,address,uint256)"
    """
    if function_hash.startswith('0x'):
        function_hash = function_hash[2:]
    try:
        signatures = get_function_db().get(function_hash.encode())
        if signatures:
            return signatures.decode()
        else:
            print(f'Error: function {function_hash} not in database')
            return None
    except KeyError:
        print(f'Error: function {function_hash} not in database')
        return None