import json
from os import listdir
import os
def collect_token(folder_prefix):

    # dumping decoded tree to invocation_tree folder
    json_file_path = folder_prefix + '/invocation_tree/'
    os.makedirs(json_file_path, exist_ok=True)
    # list all files
    jsonlist = listdir(folder_prefix + '/invocation_flow')
    for i in jsonlist:
        # root of the tree
        zero_list = []
        # a list of history dealing list
        current_list = [zero_list]
        # record the depth of current event
        current_depth = 0
        file = open(folder_prefix + '/invocation_flow/' + i)
        traces = json.load(file)
        # remember the current working list of all depths
        memory = {}
        for trace in traces:
            if (trace['type'].lower() == 'call' or
                    trace['type'].lower() == 'delegatecall' or
                    trace['type'].lower() == 'staticcall'):
                # add children
                trace['children'] = []
                # new depth
                if trace['depth'] not in memory.keys():
                    memory[trace['depth']] = [trace['from'], current_list[-1]]
                # if trace is in the current depth
                if trace['depth'] == current_depth:
                    current_list[-1].append(trace)
                    current_list.append(trace['children'])
                    current_depth += 1
                    memory[current_depth] = [trace['from'], current_list[-1]]
                # if not
                else:
                    memory[trace['depth']][1].append(trace)
                    memory[trace['depth']] = [trace['from'], memory[trace['depth']][1]]
                    current_list.append(trace['children'])
                    current_depth = trace['depth'] + 1
                    memory[current_depth] = [trace['from'], current_list[-1]]
            # find the nearest trace with same address
            if trace['type'].lower() == 'event':
                max = 0
                for i in range(len(memory)):
                    if memory[i][0] == trace['address']:
                        max = i
                memory[max][1].append(trace)
        # save tree to file
        with open(folder_prefix + '/invocation_tree/tree' + i, 'w') as jsonfile:
            json.dump(zero_list, jsonfile, indent=2)