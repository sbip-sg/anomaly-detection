import json

# Function to convert bytes to base64 encoded string
def convert_bytes_to_string(obj):
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError("Object of type {} not serializable".format(type(obj)))

# Function to transform trace JSON to graph
def foundry_to_graph(tx_hash, folder_prefix):
    # Get list of JSON files in trace_json directory with raw traces
    raw_trace = folder_prefix + '/trace_json/' + f"trace_{tx_hash}.json"
    with open(raw_trace) as f:
        input_trace = json.load(f)
    # set node dict and edge list
    nodes = {}
    sender_node = {"type": "EOA", "source": None, "value": input_trace[0]['from']}
    nodes["-1"] = sender_node
    create_parent = {}  # there is no original create relation parameters
    # first in trace
    if 'create' in input_trace[0]["kind"]:
        edges = [{"type": input_trace[0]["kind"], "from": "-1", "to": "c0"}]
        create_parent[input_trace[0]["depth"] + 1] = "c0"
    else:
        edges = [{"type": input_trace[0]["kind"], "from": "-1", "to": "0"}]
    event_id = 0
    create_id = 0
    for trace in input_trace:
        # if calling function
        if 'call' in trace["kind"]:
            call_func = trace['data'][:10]
            nodes[str(trace["call_idx"])] = {"type": trace["kind"], "source": trace["to"],
                                             "value": call_func}
            if isinstance(trace["parent"], int) and str(trace["parent"]) in nodes:
                edges.append({"type": trace["kind"], "from": str(trace["parent"]), "to": str(trace["call_idx"])})
            elif f"c{trace["parent"]}" in nodes:
                edges.append({"type": trace["kind"], "from": f"c{trace["parent"]}", "to": str(trace["call_idx"])})
            create_parent[trace["depth"] + 1] = str(trace["call_idx"])
        # if emitting event
        elif trace['kind'].lower() == 'event':
            event_func = trace['raw']['topics'][0]
            nodes[f"e{event_id}"] = {"type": trace["kind"], "source": trace["from"],
                                     "value": event_func}
            if isinstance(trace["parent"], int):
                edges.append({"type": trace["kind"], "from": str(trace["parent"]), "to": f"e{event_id}"})
            event_id += 1
        # if creating contract
        elif 'create' in trace['kind'].lower():
            nodes[f"c{create_id}"] = {"type": trace["kind"], "source": trace["from"], "value": trace["to"]}
            if trace["depth"] in create_parent:
                edges.append({"type": trace["kind"], "from": create_parent[trace["depth"]], "to": f"c{create_id}"})
            create_id += 1
        # if self-destruction
        elif trace['kind'].lower() == 'selfdestruct':
            edges.append({"type": trace["kind"], "from": trace["address"], "to": trace["address"]})

    trace_graph = {"nodes": nodes, "edges": edges}
    # dump the trace graph to a json file
    with open(folder_prefix + f'/trace_json/graph_{tx_hash}.json', 'w') as jsonfile:
        json.dump(trace_graph, jsonfile, default=convert_bytes_to_string, indent=2)
