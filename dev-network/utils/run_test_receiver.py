# The receiver is called by run_lab and receives the testcases as json

# Step by step action by sender
# - For each test case
#   - calculate the expected results according to the given data
#       - get the actual control plane data from the runtime json definitions
#       - apply the patches to the runtime definiton
#   - sniff for the specified amount of packets using scapy
#   - verify if the values in the received packets match the precalculated results
#   - write the received IOAM data to a file in json format

import json
import logging
import os
import testing.calc
import argparse
import testing.utils
from scapy.all import *

# datastructure that holds all energy efficiency related actions and the corresponding value bit size
component_actions = {
    "MyEgress.process_efficiency_indicator.get_carbon_metric_energy_mix": {
        "value_bit_size": 7
    },
    "MyEgress.process_efficiency_indicator.get_carbon_metric_idle_power": {
        "value_bit_size": 10
    },
    "MyEgress.process_efficiency_indicator.get_carbon_metric_embedded_carbon": {
        "value_bit_size": 16
    },
}

# test infrastructure specific constants
SENDER_IP_ADDRESS = "2001:DB8:64::10"
INITIAL_HOP_LIMIT = 60
NODE_LIST_LEN_BITS = 128  # NodeLen (32 Bit) * NumNodes (4)
NODE_LIST_LEN_ITEMS = 4


# scapy custom packet classes definition
class GreenNetworkingIPv6ExtHdrHopByHop(Packet):
    name = "IPv6 Hop by Hop Extension Header (Green Networking)"
    fields_desc = [
        XByteField("nextHeader", None),
        XByteField("length", None),
    ]


class IoamPreallocatedTraceOption(Packet):
    name = "IOAM Trace Option"
    fields_desc = [
        XByteField("type", None),
        XByteField("length", None),
        XByteField("reserved", None),
        XByteField("option_type", None),
        XBitField("namespace_id", None, 16),
        XBitField("node_length", None, 5),
        XBitField("flags", None, 4),
        XBitField("remaining_len", None, 7),
        XBitField("trace_type", None, 24),
        XByteField("ioam_reserved", None),
        XBitField("node_list", None, NODE_LIST_LEN_BITS),
    ]


class IoamAggregationOption(Packet):
    name = "IOAM Aggregation Option"
    fields_desc = [
        XByteField("type", None),
        XByteField("length", None),
        XByteField("reserved", None),
        XByteField("option_type", None),
        XBitField("namespace_id", None, 16),
        XBitField("flags", None, 4),
        XBitField("ioam_reserved", None, 12),
        XBitField("ioam_data_param", None, 24),
        XBitField("aggregator", None, 8),
        XBitField("aggregate", None, 32),
        XBitField("auxil_data_node_id", None, 24),
        XBitField("hop_count", None, 8),
    ]


# bind custom options to the IPv6 header
bind_layers(scapy.layers.inet6.IPv6, GreenNetworkingIPv6ExtHdrHopByHop, nh=0)
bind_layers(GreenNetworkingIPv6ExtHdrHopByHop, IoamPreallocatedTraceOption)
bind_layers(IoamPreallocatedTraceOption, IoamAggregationOption)
bind_layers(IoamAggregationOption, scapy.layers.inet6.PadN)


# initialize argparse
def get_args():
    cwd = os.getcwd()
    default_logs = os.path.join(cwd, "logs/testing")
    default_runtimes = os.path.join(cwd, "dev-network/tmp_runtimes")
    parser = argparse.ArgumentParser(
        description="Energy Efficiency Indiciator Test Listener"
    )
    parser.add_argument(
        "-l", "--log-dir", type=str, required=False, default=default_logs
    )
    parser.add_argument(
        "-r", "--runtime-dir", type=str, required=False, default=default_runtimes
    )
    parser.add_argument("-n", "--host-name", type=str, required=True)
    parser.add_argument(
        "-t",
        "--testcases",
        help="Path to testcase defintion file",
        type=str,
        required=True,
    )
    parser.add_argument(
        "-e",
        "--export",
        help="Boolean flag to indicate wether the received data should be exported",
        required=False,
        default=False,
        action="store_true",
    )
    return parser.parse_args()


def get_relevant_testcases(testcases_file, paths, host):
    with open(testcases_file, "r") as f:
        resources = json.load(f)
    my_tests = []
    # filter for tests which are on a class where the <host> is specified as destination
    for test in resources["testcases"]:
        path_id = test["path"]
        path = paths[path_id]
        if path["dst"] == host:
            my_tests.append(test)
    return my_tests


def validate_header_field(field_name, expected, received, sequence):
    # compare expected and received header fields and log result accordingly
    if expected != received:
        test["passed"] = False
        logging.error(
            "Test failed, packet %s/%s field invalid (%s: expected = %s / received = %s) (id: %s)",
            sequence,
            test["num_packets"],
            field_name,
            expected,
            received,
            test["id"],
        )
    else:
        logging.info(
            "Test passed, packet %s/%s field valid (%s: expected = %s / received = %s) (id: %s)",
            sequence,
            test["num_packets"],
            field_name,
            expected,
            received,
            test["id"],
        )


def validate_ioam_aggregation_header(packets, path, aggregator, nodes_component_data):
    logging.info("Validating IOAM aggreagation header fields")

    # set generic values
    aggregate_val = 0
    aggregator_val = 0
    node_id = 0
    hop_count_val = len(path["nodes"])

    # set aggregator type specific values
    if aggregator == "sum":
        aggregate_val = testing.calc.calculate_pei(path, nodes_component_data)
        aggregator_val = 1
        node_id = testing.utils.get_last_node_in_path(path)
    elif aggregator == "min":
        (aggregate_val, node_id) = testing.calc.get_min_hei(path, nodes_component_data)
        aggregator_val = 2
    elif aggregator == "max":
        (aggregate_val, node_id) = testing.calc.get_max_hei(path, nodes_component_data)
        aggregator_val = 4
    else:
        raise ValueError("Invalid aggregator value '%s' supplied" % aggregator)

    # craft expected scapy ioam aggregation layer
    expected = IoamAggregationOption(
        type=0x31,
        length=18,
        reserved=0,
        option_type=0x20,
        namespace_id=0,
        flags=0,
        ioam_reserved=0,
        ioam_data_param=0xFF,
        aggregator=aggregator_val,
        aggregate=aggregate_val,
        auxil_data_node_id=node_id,
        hop_count=hop_count_val,
    )

    # validate all ioam aggregation header fields of each received packet
    for id, packet in enumerate(packets):
        received = packet.getlayer(IoamAggregationOption)
        validate_header_field("type", expected.type, received.type, id + 1)
        validate_header_field("length", expected.length, received.length, id + 1)
        validate_header_field("reserved", expected.reserved, received.reserved, id + 1)
        validate_header_field(
            "option_type", expected.option_type, received.option_type, id + 1
        )
        validate_header_field(
            "namespace_id", expected.namespace_id, received.namespace_id, id + 1
        )
        validate_header_field("flags", expected.flags, received.flags, id + 1)
        validate_header_field(
            "ioam_reserved", expected.ioam_reserved, received.ioam_reserved, id + 1
        )
        validate_header_field(
            "ioam_data_param",
            expected.ioam_data_param,
            received.ioam_data_param,
            id + 1,
        )
        validate_header_field(
            "aggregator", expected.aggregator, received.aggregator, id + 1
        )
        validate_header_field(
            "aggregate", expected.aggregate, received.aggregate, id + 1
        )
        validate_header_field(
            "auxil_data_node_id",
            expected.auxil_data_node_id,
            received.auxil_data_node_id,
            id + 1,
        )
        validate_header_field(
            "hop_count", expected.hop_count, received.hop_count, id + 1
        )


def validate_ioam_trace_header(packets, path):
    logging.info("Validating IOAM trace header fields")

    # set generic values
    hop_count_val = len(path["nodes"])
    remaining_len_val = 0
    flags_val = 0
    node_list_val = testing.utils.get_node_list_raw(
        path, INITIAL_HOP_LIMIT, NODE_LIST_LEN_ITEMS
    )

    # set node list length dependent values
    if NODE_LIST_LEN_ITEMS > hop_count_val:
        remaining_len_val = NODE_LIST_LEN_ITEMS - hop_count_val
    elif NODE_LIST_LEN_ITEMS < hop_count_val:
        logging.info(
            "Expecting overflow: Path %s contains more than %s nodes",
            path["id"],
            NODE_LIST_LEN_ITEMS,
        )
        # overflow flag set
        flags_val = 8

    # craft expected scapy ioam aggregation layer
    expected = IoamPreallocatedTraceOption(
        type=0x31,
        length=26,
        reserved=0,
        option_type=0,
        namespace_id=0,
        node_length=1,
        flags=flags_val,
        remaining_len=remaining_len_val,
        trace_type=0x800000,
        ioam_reserved=0,
        node_list=node_list_val,
    )

    # validate all ioam trace header fields of each received packet
    for id, packet in enumerate(packets):
        received = packet.getlayer(IoamPreallocatedTraceOption)
        validate_header_field("type", expected.type, received.type, id + 1)
        validate_header_field("length", expected.length, received.length, id + 1)
        validate_header_field("reserved", expected.reserved, received.reserved, id + 1)
        validate_header_field(
            "option_type", expected.option_type, received.option_type, id + 1
        )
        validate_header_field(
            "namespace_id", expected.namespace_id, received.namespace_id, id + 1
        )
        validate_header_field(
            "node_length", expected.node_length, received.node_length, id + 1
        )
        validate_header_field("flags", expected.flags, received.flags, id + 1)
        validate_header_field(
            "remaining_len", expected.remaining_len, received.remaining_len, id + 1
        )
        validate_header_field(
            "trace_type", expected.trace_type, received.trace_type, id + 1
        )
        validate_header_field(
            "ioam_reserved", expected.ioam_reserved, received.ioam_reserved, id + 1
        )
        validate_header_field(
            "node_list", expected.node_list, received.node_list, id + 1
        )


def export_packets_to_json(packets, test, export_file):
    # list for the datastructure
    packetlist = []

    # datastructure for the efficiency data
    path_efficiency_data_entry = {
        "test_id": None,
        "timestamp": None,
        "size": None,
        "ethernet": {
            "src": None,
            "dst": None,
        },
        "ipv6": {"src": None, "dst": None, "hop_limit": None},
        "hop_by_hop_option": {
            "ioam_option_tracing": {
                "type": None,
                "length": None,
                "reserved": None,
                "option_type": None,
                "namespace_id": None,
                "node_length": None,
                "flags": None,
                "remaining_length": None,
                "trace_type": None,
                "ioam_reserved": None,
                "node_list": None,
            },
            "ioam_option_aggregation": {
                "type": None,
                "length": None,
                "reserved": None,
                "option_type": None,
                "namespace_id": None,
                "flags": None,
                "ioam_reserved": None,
                "ioam_data_param": None,
                "aggregator": None,
                "aggregate": None,
                "auxil_data_node_id": None,
                "hop_count": None,
            },
        },
    }

    for packet in packets:
        ioam_trace_data = packet.getlayer(IoamPreallocatedTraceOption)
        ioam_aggregation_data = packet.getlayer(IoamAggregationOption)

        entry = path_efficiency_data_entry.copy()

        # Add general parameters to the datastructure
        entry["test_id"] = test["id"]
        entry["timestamp"] = time.time_ns()
        entry["size"] = len(packet)

        # Add Ethernet parameters to the datastructure
        entry["ethernet"]["src"] = packet["Ethernet"].src
        entry["ethernet"]["dst"] = packet["Ethernet"].dst

        # Add IPv6 parameters to the datastructure
        entry["ipv6"]["src"] = packet["IPv6"].src
        entry["ipv6"]["dst"] = packet["IPv6"].dst
        entry["ipv6"]["hop_limit"] = packet["IPv6"].hlim

        # Add ioam tracing parameters to the datastructure
        entry["hop_by_hop_option"]["ioam_option_tracing"][
            "type"
        ] = ioam_trace_data.type
        entry["hop_by_hop_option"]["ioam_option_tracing"][
            "length"
        ] = ioam_trace_data.length
        entry["hop_by_hop_option"]["ioam_option_tracing"][
            "reserved"
        ] = ioam_trace_data.reserved
        entry["hop_by_hop_option"]["ioam_option_tracing"][
            "option_type"
        ] = ioam_trace_data.option_type
        entry["hop_by_hop_option"]["ioam_option_tracing"][
            "namespace_id"
        ] = ioam_trace_data.namespace_id
        entry["hop_by_hop_option"]["ioam_option_tracing"][
            "node_length"
        ] = ioam_trace_data.node_length
        entry["hop_by_hop_option"]["ioam_option_tracing"][
            "flags"
        ] = ioam_trace_data.flags
        entry["hop_by_hop_option"]["ioam_option_tracing"][
            "remaining_length"
        ] = ioam_trace_data.remaining_len
        entry["hop_by_hop_option"]["ioam_option_tracing"][
            "trace_type"
        ] = ioam_trace_data.trace_type
        entry["hop_by_hop_option"]["ioam_option_tracing"][
            "ioam_reserved"
        ] = ioam_trace_data.ioam_reserved
        entry["hop_by_hop_option"]["ioam_option_tracing"][
            "node_list"
        ] = testing.utils.parse_node_list(ioam_trace_data.node_list)

        # Add ioam aggregation parameters to the datastructure
        entry["hop_by_hop_option"]["ioam_option_aggregation"][
            "type"
        ] = ioam_aggregation_data.type
        entry["hop_by_hop_option"]["ioam_option_aggregation"][
            "length"
        ] = ioam_aggregation_data.length
        entry["hop_by_hop_option"]["ioam_option_aggregation"][
            "reserved"
        ] = ioam_aggregation_data.reserved
        entry["hop_by_hop_option"]["ioam_option_aggregation"][
            "option_type"
        ] = ioam_aggregation_data.option_type
        entry["hop_by_hop_option"]["ioam_option_aggregation"][
            "namespace_id"
        ] = ioam_aggregation_data.namespace_id
        entry["hop_by_hop_option"]["ioam_option_aggregation"][
            "flags"
        ] = ioam_aggregation_data.flags
        entry["hop_by_hop_option"]["ioam_option_aggregation"][
            "ioam_reserved"
        ] = ioam_aggregation_data.ioam_reserved
        entry["hop_by_hop_option"]["ioam_option_aggregation"][
            "ioam_data_param"
        ] = ioam_aggregation_data.ioam_data_param
        entry["hop_by_hop_option"]["ioam_option_aggregation"][
            "aggregator"
        ] = ioam_aggregation_data.aggregator
        entry["hop_by_hop_option"]["ioam_option_aggregation"][
            "aggregate"
        ] = ioam_aggregation_data.aggregate
        entry["hop_by_hop_option"]["ioam_option_aggregation"][
            "auxil_data_node_id"
        ] = ioam_aggregation_data.auxil_data_node_id
        entry["hop_by_hop_option"]["ioam_option_aggregation"][
            "hop_count"
        ] = ioam_aggregation_data.hop_count

        packetlist.append(entry)

    if os.path.exists(export_file):
        with open(export_file, "r+") as f:
            exported_packetlist = json.load(f)
            updated_export = exported_packetlist + packetlist
            f.seek(0)
            json.dump(updated_export, f, indent=2)
            f.truncate()
    else:
        with open(export_file, "w") as f:
            json.dump(packetlist, f, indent=2)


if __name__ == "__main__":
    args = get_args()
    # configure logging
    logging.basicConfig(
        filename=f"{args.log_dir}/{args.host_name}-test-receiver.log",
        format="%(asctime)s:%(levelname)s:%(message)s",
        level=logging.INFO,
    )
    logging.info("Starting test receiver on %s", args.host_name)
    # initialize base datastructures
    paths = testing.utils.get_path_dict(args.testcases)
    tests = get_relevant_testcases(args.testcases, paths, args.host_name)
    # clear previously exported data
    workdir = os.getcwd()
    export_file_path = f"{workdir}/dev-network/demo/{args.host_name}.json"
    if args.export and os.path.exists(export_file_path):
        os.remove(export_file_path)

    for test in tests:
        logging.info("Waiting for packets (id: %s)", test["id"])
        # listen for n transmissioned packets from the sending host
        packets = sniff(filter=f"host {SENDER_IP_ADDRESS}", count=test["num_packets"])
        # get nodes components data for current test (base information to do efficiency calculation)
        path = paths[test["path"]]
        test_runtime_dir = os.path.join(args.runtime_dir, test["id"])
        nodes_component_data = testing.utils.get_nodes_component_data(
            path, component_actions, test_runtime_dir
        )
        # initialize test state indication
        test["passed"] = True
        # validate values in IOAM aggregation header
        validate_ioam_aggregation_header(
            packets, path, test["ioam_aggregation"]["aggregator"], nodes_component_data
        )
        # validate values in IOAM tracing header
        validate_ioam_trace_header(packets, path)

        # log test execution result
        if test["passed"]:
            logging.info("TEST PASSED (id: %s)", test["id"])
        else:
            logging.error("TEST FAILED (id: %s)", test["id"])

        # export packets data
        if args.export:
            export_packets_to_json(packets, test, export_file_path)
