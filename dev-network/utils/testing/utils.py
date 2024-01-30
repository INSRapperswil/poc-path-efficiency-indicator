import json
import logging
import os

NODE_LIST_LEN = 128  # NodeLen (32 Bit) * NumNodes (4)


def get_path_dict(testcases_file):
    with open(testcases_file, "r") as f:
        resources = json.load(f)
    path_dict = {}
    # store the path id as key of the dictionary and the path itself as value
    for path in resources["paths"]:
        if path["id"] in path_dict:
            raise ValueError("Duplicate path id '%s' defined." % path["id"])
        path_dict[path["id"]] = path
    return path_dict


def get_path_destinations(paths):
    destinations = set()
    # store the destinations of all paths in a set
    for _, path in paths.items():
        destinations.add(path["dst"])
    return destinations


def get_last_node_in_path(path):
    # return the id of the last element in the node list of a path
    return path["nodes"][-1]["id"]


def get_node_list_raw(path, initial_hop_limit, node_list_len):
    logging.info("Generating raw node list for path %s", path["id"])
    node_list = 0
    hop_limit = initial_hop_limit
    # get first <node_list_len> nodes from the path (required to reflect the max number of tracable nodes limitation)
    nodes = path["nodes"][:node_list_len]
    # add the trace data to the node list in the hop_lim and node_id short format rfc9197
    for node in nodes:
        hop_limit -= 1
        # make free space for the hop limit
        node_list = node_list << 8
        # add the hop limit to the node list as the 8 least significant bits
        node_list = node_list | hop_limit
        # make free space for the node id
        node_list = node_list << 24
        # add the node id to the node list as the 24 least significant bits
        node_list = node_list | node["id"]
    return node_list


def parse_node_list(nodelist_raw):
    nodelist = []
    offset = 0
    fieldlength = 8
    while offset < NODE_LIST_LEN:
        temp = nodelist_raw >> NODE_LIST_LEN - (fieldlength + offset)
        temp = temp & 2**fieldlength - 1
        offset += fieldlength
        if fieldlength == 8:
            nodelist_entry = {}
            nodelist_entry["hop_limit"] = temp
            fieldlength = 24
        else:
            nodelist_entry["node_id"] = temp
            fieldlength = 8
            nodelist.append(nodelist_entry)
    return nodelist


def get_nodes_component_data(path, components, runtime_dir):
    nodes = []
    # get a list of nodes of the path containing node information (id and name) as well as all component values
    for node in path["nodes"]:
        node_data = {"name": node["name"], "id": node["id"]}
        # specify test specific runtime file
        runtime_file = os.path.join(runtime_dir, f"{node_data['name']}-runtime.json")
        node_components = {}
        # read component values from specific runtime file
        with open(runtime_file, "r") as f:
            runtime = json.load(f)
            # find energy efficiency component relevant table entries
            for table in runtime["table_entries"]:
                if table["action_name"] in components:
                    logging.info(
                        "Setting action params of node %s and action %s",
                        node_data["name"],
                        table["action_name"],
                    )
                    # set the node components action to the values specified in the specific runtime file
                    node_components[table["action_name"]] = table["action_params"]
                    # set the size in bits of the value for the specific component
                    node_components[table["action_name"]][
                        "value_bit_size"
                    ] = components[table["action_name"]]["value_bit_size"]
                    # set the components of the current node in the target data structure
                    node_data["components"] = node_components
        # add the determined node data dictionary (key: name, id and components) to the node list
        nodes.append(node_data)
    return nodes
