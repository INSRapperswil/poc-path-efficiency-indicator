import json
import logging
import os

VALUE_NORMALIZED_BIT_SIZE = 15


def normalize(value, type_size):
    # map value out of a smaller range to the larger normalized range (upscale)
    if type_size < VALUE_NORMALIZED_BIT_SIZE:
        return value << (VALUE_NORMALIZED_BIT_SIZE - type_size)
    # map value out of a larger range to the smaller normalized range (downscale)
    elif type_size > VALUE_NORMALIZED_BIT_SIZE:
        return value >> (type_size - VALUE_NORMALIZED_BIT_SIZE)


def invert(value_normalized, inverse):
    # invert the range of the value
    if inverse == True:
        return (2**VALUE_NORMALIZED_BIT_SIZE - 1) - value_normalized
    return value_normalized


def weight(value_inverted, weight):
    # apply positive weight
    if weight > 1:
        return value_inverted << 1
    # apply negative weight
    elif weight < 1:
        return value_inverted >> 1
    return value_inverted


def calculate_hei(node):
    logging.info("Calculating HEI for node %s", node["name"])
    hop_efficiency_indicator = 0
    # sum up all component values to the HEI
    for action_name, action_params in node["components"].items():
        logging.info(
            "Calculating component value for action %s on node %s",
            action_name,
            node["name"],
        )
        value_normalized = normalize(
            action_params["value"], action_params["value_bit_size"]
        )
        value_inverted = invert(value_normalized, action_params["inverse"])
        value_weighted = weight(value_inverted, action_params["weight"])
        hop_efficiency_indicator += value_weighted
    return hop_efficiency_indicator


def calculate_compoennt_val_by_action(node, action_name):
    logging.info(
        "Calculating component value for action %s on node %s",
        action_name,
        node["name"],
    )
    action_params = node["components"][action_name]
    value_normalized = normalize(
        action_params["value"], action_params["value_bit_size"]
    )
    value_inverted = invert(value_normalized, action_params["inverse"])
    value_weighted = weight(value_inverted, action_params["weight"])
    return value_weighted


def get_min_hei(path, nodes):
    logging.info("Getting minimum HEI in path %s", path["id"])
    # initialize the minimum HEI variable with the aggregate maximum value
    min_hei = 2**32 - 1
    node_id = 0
    # calculate the HEI of each node in the path and check if it is smaller than the already determined
    for node in nodes:
        current_hei = calculate_hei(node)
        if current_hei < min_hei:
            min_hei = current_hei
            node_id = node["id"]
    return (min_hei, node_id)


def get_max_hei(path, nodes):
    logging.info("Getting maximum HEI in path %s", path["id"])
    # initialize the maximum HEI variable with the aggregate minimum value
    max_hei = 0
    node_id = 0
    # calculate the HEI of each node in the path and check if it is larger than the already determined
    for node in nodes:
        current_hei = calculate_hei(node)
        if current_hei > max_hei:
            max_hei = current_hei
            node_id = node["id"]
    return (max_hei, node_id)


def calculate_pei(path, nodes):
    logging.info("Calculating PEI for path %s", path["id"])
    path_efficiency_indicator = 0
    # calculate the HEI of each node in the path and sum them up to the PEI
    for node in nodes:
        path_efficiency_indicator += calculate_hei(node)
    return path_efficiency_indicator

def calculate_pei_by_component(path, nodes):
    logging.info("Calculating PEI by component for path %s", path["id"])
    component_name_action_dict = {
        "energy_mix": "MyEgress.process_efficiency_indicator.get_carbon_metric_energy_mix",
        "idle_power": "MyEgress.process_efficiency_indicator.get_carbon_metric_idle_power",
        "embedded_carbon": "MyEgress.process_efficiency_indicator.get_carbon_metric_embedded_carbon"
    }
    pei_by_component_dict = {}
    path_efficiency_indicator = 0
    for component_name, component_action_name in component_name_action_dict.items():
        pei_by_component_dict[component_name] = 0
        for node in nodes:
            pei_by_component_dict[component_name] += calculate_compoennt_val_by_action(node, component_action_name)
        path_efficiency_indicator += pei_by_component_dict[component_name]
    return path_efficiency_indicator, pei_by_component_dict
