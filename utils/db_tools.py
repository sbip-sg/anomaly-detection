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


def save_new_line(entity: dict, filename: str, primary_keys: list, appending: bool = False):
    """
    Saves a single entity (dictionary) to a CSV file, optionally adding an ID column if appending is True.

    Parameters:
    - entity (dict): The entity to save.
    - filename (str): The CSV file to save to.
    - primary_keys (list): The primary keys to check for duplicates.
    - appending (bool): If True, adds an 'id' column as a unique primary key.
    """
    # Check if file format is correct
    if not filename.endswith('.csv'):
        print("Error: File format must be .csv")
        return

    # Check if primary keys are valid
    if not all(key in entity for key in primary_keys) and not appending:
        print("Error: All primary keys must be present in the entity.")
        return

    file_exists = os.path.isfile(filename)

    try:
        # If appending, determine the next unique ID
        if appending:
            next_id = 1
            if file_exists:
                with open(filename, mode='r', newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    ids = [int(row['id']) for row in reader if 'id' in row]
                    next_id = max(ids) + 1 if ids else 1
            entity['id'] = next_id

        # If the file exists, read it to check for duplicates
        if file_exists:
            with open(filename, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Check if all primary key values match
                    if all(row[key] == str(entity[key]) for key in primary_keys):
                        print("Duplicate entry found. Not inserting.")
                        return

        # Open the file in append mode to add the new line
        with open(filename, mode='a', newline='', encoding='utf-8') as file:
            fieldnames = list(entity.keys())
            if appending and 'id' not in fieldnames:
                fieldnames.append('id')
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            # Write the header if the file is new
            if not file_exists:
                writer.writeheader()
            writer.writerow(entity)
            print(f"Data successfully saved to {filename}.")

    except Exception as e:
        print(f"Error saving data: {e}")



def save_multi_lines(entities: list, filename: str, primary_keys: list, appending: bool = False):
    """
    Saves multiple entities (dictionaries) to a CSV file, checking for duplicates based on primary keys.

    Parameters:
    - entities (list): A list of entities (dictionaries) to save.
    - filename (str): The CSV file to save to.
    - primary_keys (list): The primary keys to check for duplicates.
    - appending (bool): If True, adds an 'id' column as a unique primary key.
    """
    # Check if file format is correct
    if not filename.endswith('.csv'):
        print("Error: File format must be .csv")
        return

    # Check if primary keys are valid for all entities
    if not all(all(key in entity for key in primary_keys) for entity in entities) and not appending:
        print("Error: All primary keys must be present in each entity.")
        return

    file_exists = os.path.isfile(filename)

    try:
        # If appending, calculate the next unique ID
        next_id = 1
        if appending and file_exists:
            with open(filename, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                ids = [int(row['id']) for row in reader if 'id' in row]
                next_id = max(ids) + 1 if ids else 1

        # Assign IDs to entities if appending
        if appending:
            for entity in entities:
                entity['id'] = next_id
                next_id += 1

        # Open the file in append mode to add new lines
        with open(filename, mode='a', newline='', encoding='utf-8') as file:
            fieldnames = list(entities[0].keys())
            if appending and 'id' not in fieldnames:
                fieldnames.append('id')
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            # Write the header if the file is new
            if not file_exists:
                writer.writeheader()

            # Loop through each entity and check for duplicates
            for entity in entities:
                duplicate = False
                if file_exists:
                    with open(filename, mode='r', newline='', encoding='utf-8') as check_file:
                        reader = csv.DictReader(check_file)
                        for row in reader:
                            # Check if all primary key values match
                            if all(row[key] == str(entity[key]) for key in primary_keys):
                                print(f"Duplicate entry found for entity {entity}. Not inserting.")
                                duplicate = True
                                break
                if not duplicate:
                    writer.writerow(entity)
                    print(f"Data for {entity} successfully saved to {filename}.")

    except Exception as e:
        print(f"Error saving data: {e}")


def append_dataframe_to_csv(df: pd.DataFrame, filename: str, foreign_keys: dict, index: bool = False):
    """
    Appends a pandas DataFrame to a CSV file, checking for duplicates based on foreign_keys.
    The index continues from the last index in the existing CSV file.

    Parameters:
    - df (pd.DataFrame): The DataFrame to append.
    - filename (str): The name of the CSV file to append to.
    - foreign_keys (dict): A dictionary mapping column names to their corresponding foreign key values.
    - index (bool): Whether to include the DataFrame index in the CSV file.
    """
    if not filename.endswith('.csv'):
        print("Error: File format must be .csv")
        return

    file_exists = os.path.isfile(filename)

    try:
        if file_exists:
            # Read the existing file to check for duplicates
            existing_df = pd.read_csv(filename)

            # Loop over foreign_keys to check for duplicates
            for key, value in foreign_keys.items():
                if key in df.columns:
                    # Check if any row in df matches the foreign key value in the existing DataFrame
                    if (existing_df[key] == value).any():
                        print(f"Duplicate found for {key} = {value}. DataFrame will not be appended.")
                        return  # Early return if duplicate is found

            # Continue the index from the last row of the existing CSV
            last_index = existing_df.index[-1] if not existing_df.empty else -1
            df.index = range(last_index + 1, last_index + 1 + len(df))

        # Append the DataFrame to the CSV file
        df.to_csv(
            filename,
            mode='a',  # Append mode
            header=not file_exists,  # Write header only if the file does not exist
            index=index,  # Include the modified index
            encoding='utf-8'
        )
        print(f"DataFrame successfully appended to {filename}.")
    except Exception as e:
        print(f"Error appending DataFrame to file: {e}")

def get_lines(filename: str, restrictions: dict = None):
    # Check if the file exists
    if not filename.endswith('.csv'):
        print("Error: File format must be .csv")
        return []

    try:
        results = []
        with open(filename, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # If restrictions are provided, filter rows
                if restrictions:
                    match = all(row.get(key) == str(value) for key, value in restrictions.items())
                    if not match:
                        continue
                results.append(row)

        return results

    except FileNotFoundError:
        print(f"Error: File {filename} does not exist.")
        return []
    except Exception as e:
        print(f"Error reading file: {e}")
        return []