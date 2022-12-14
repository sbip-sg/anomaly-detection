import json

def open_json(file='database/topics.json'):
    # read json file
    f = open(file, 'r')
    if len(f.read()) == 0:
        db_dict = {}
    else:
        f.seek(0)
        db_dict = json.load(f)
    f.close()
    return db_dict

# add database into file


def store_json(file, database):
    db_dict = open_json(file)

    # add new database and write it back
    f = open(file, 'w')
    db_dict.update(database)
    print("num = ", len(db_dict))
    db_json = json.dumps(db_dict, indent=4)
    f.write(db_json)
    f.close()
