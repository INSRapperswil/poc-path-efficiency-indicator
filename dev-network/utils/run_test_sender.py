#!/usr/bin/env python3
# Copyright 2013-present Barefoot Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Adapted by Robert MacDavid (macdavid@cs.princeton.edu) from scripts found in
# the p4app repository (https://github.com/p4lang/p4app)
#
# We encourage you to dissect this script to better understand the BMv2/Mininet
# environment used by the P4 tutorial.
#
import argparse
import json
import os
import logging

import subprocess
from time import sleep
from shutil import copy
from datetime import datetime
import uuid

import p4runtime_lib.simple_controller
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.topo import Topo
from p4_mininet import P4Host, P4Switch
from p4runtime_switch import P4RuntimeSwitch

import testing.utils


def configureP4Switch(**switch_args):
    """Helper class that is called by mininet to initialize
    the virtual P4 switches. The purpose is to ensure each
    switch's thrift server is using a unique port.
    """
    if "sw_path" in switch_args and "grpc" in switch_args["sw_path"]:
        # If grpc appears in the BMv2 switch target, we assume will start P4Runtime
        class ConfiguredP4RuntimeSwitch(P4RuntimeSwitch):
            def __init__(self, *opts, **kwargs):
                kwargs.update(switch_args)
                P4RuntimeSwitch.__init__(self, *opts, **kwargs)

            def describe(self):
                print("%s -> gRPC port: %d" % (self.name, self.grpc_port))

        return ConfiguredP4RuntimeSwitch
    else:

        class ConfiguredP4Switch(P4Switch):
            next_thrift_port = 9090

            def __init__(self, *opts, **kwargs):
                global next_thrift_port
                kwargs.update(switch_args)
                kwargs["thrift_port"] = ConfiguredP4Switch.next_thrift_port
                ConfiguredP4Switch.next_thrift_port += 1
                P4Switch.__init__(self, *opts, **kwargs)

            def describe(self):
                print("%s -> Thrift port: %d" % (self.name, self.thrift_port))

        return ConfiguredP4Switch


class ExerciseTopo(Topo):
    """The mininet topology class for the P4 tutorial exercises."""

    def __init__(self, hosts, switches, links, log_dir, bmv2_exe, pcap_dir, **opts):
        Topo.__init__(self, **opts)
        host_links = []
        switch_links = []

        # assumes host always comes first for host<-->switch links
        for link in links:
            if link["node1"][0] == "h":
                host_links.append(link)
            else:
                switch_links.append(link)

        for sw, params in switches.items():
            if "program" in params:
                switchClass = configureP4Switch(
                    sw_path=bmv2_exe,
                    json_path=params["program"],
                    log_console=True,
                    pcap_dump=pcap_dir,
                )
            else:
                # add default switch
                switchClass = None
            self.addSwitch(sw, log_file="%s/%s.log" % (log_dir, sw), cls=switchClass)

        for link in host_links:
            host_name = link["node1"]
            sw_name, sw_port = self.parse_switch_node(link["node2"])
            host_ip = hosts[host_name]["ip"]
            host_mac = hosts[host_name]["mac"]
            self.addHost(host_name, ip=host_ip, mac=host_mac)
            self.addLink(
                host_name,
                sw_name,
                delay=link["latency"],
                bw=link["bandwidth"],
                port2=sw_port,
            )

        for link in switch_links:
            sw1_name, sw1_port = self.parse_switch_node(link["node1"])
            sw2_name, sw2_port = self.parse_switch_node(link["node2"])
            self.addLink(
                sw1_name,
                sw2_name,
                port1=sw1_port,
                port2=sw2_port,
                delay=link["latency"],
                bw=link["bandwidth"],
            )

    def parse_switch_node(self, node):
        assert len(node.split("-")) == 2
        sw_name, sw_port = node.split("-")
        try:
            sw_port = int(sw_port[1:])
        except:
            raise Exception("Invalid switch node in topology file: {}".format(node))
        return sw_name, sw_port


class ExerciseRunner:
    """
    Attributes:
        log_dir  : string   // directory for mininet log files
        pcap_dir : string   // directory for mininet switch pcap files
        quiet    : bool     // determines if we print logger messages

        hosts    : dict<string, dict> // mininet host names and their associated properties
        switches : dict<string, dict> // mininet switch names and their associated properties
        links    : list<dict>         // list of mininet link properties

        switch_json : string // json of the compiled p4 example
        bmv2_exe    : string // name or path of the p4 switch binary

        topo : Topo object   // The mininet topology instance
        net : Mininet object // The mininet instance

    """

    def format_latency(self, l):
        """Helper method for parsing link latencies from the topology json."""
        if isinstance(l, str):
            return l
        else:
            return str(l) + "ms"

    def __init__(
        self,
        topo_file,
        log_dir,
        pcap_dir,
        switch_json,
        bmv2_exe="simple_switch",
        quiet=False,
    ):
        """Initializes some attributes and reads the topology json. Does not
        actually run the exercise. Use run_exercise() for that.

        Arguments:
            topo_file : string    // A json file which describes the exercise's
                                     mininet topology.
            log_dir  : string     // Path to a directory for storing exercise logs
            pcap_dir : string     // Ditto, but for mininet switch pcap files
            switch_json : string  // Path to a compiled p4 json for bmv2
            bmv2_exe    : string  // Path to the p4 behavioral binary
            quiet : bool          // Enable/disable script debug messages
        """

        self.quiet = quiet
        logging.info("Reading topology file.")
        with open(topo_file, "r") as f:
            topo = json.load(f)
        self.hosts = topo["hosts"]
        self.switches = topo["switches"]
        self.links = self.parse_links(topo["links"])

        # Ensure all the needed directories exist and are directories
        for dir_name in [log_dir, pcap_dir]:
            if not os.path.isdir(dir_name):
                if os.path.exists(dir_name):
                    raise Exception("'%s' exists and is not a directory!" % dir_name)
                os.mkdir(dir_name)
        self.log_dir = log_dir
        self.pcap_dir = pcap_dir
        self.switch_json = switch_json
        self.bmv2_exe = bmv2_exe

    def run_exercise(self):
        """Sets up the mininet instance, programs the switches,
        and starts the mininet CLI. This is the main method to run after
        initializing the object.
        """
        # Initialize mininet with the topology specified by the config
        self.create_network()
        self.net.start()
        sleep(1)

        # some programming that must happen after the net has started
        self.program_hosts()
        self.program_switches()

        # wait for that to finish. Not sure how to do this better
        sleep(1)

    def parse_links(self, unparsed_links):
        """Given a list of links descriptions of the form [node1, node2, latency, bandwidth]
        with the latency and bandwidth being optional, parses these descriptions
        into dictionaries and store them as self.links
        """
        links = []
        for link in unparsed_links:
            # make sure each link's endpoints are ordered alphabetically
            (
                s,
                t,
            ) = (
                link[0],
                link[1],
            )
            if s > t:
                s, t = t, s

            link_dict = {"node1": s, "node2": t, "latency": "0ms", "bandwidth": None}
            if len(link) > 2:
                link_dict["latency"] = self.format_latency(link[2])
            if len(link) > 3:
                link_dict["bandwidth"] = link[3]

            if link_dict["node1"][0] == "h":
                assert (
                    link_dict["node2"][0] == "s"
                ), "Hosts should be connected to switches, not " + str(
                    link_dict["node2"]
                )
            links.append(link_dict)
        return links

    def create_network(self):
        """Create the mininet network object, and store it as self.net.

        Side effects:
            - Mininet topology instance stored as self.topo
            - Mininet instance stored as self.net
        """
        logging.info("Building mininet topology.")

        defaultSwitchClass = configureP4Switch(
            sw_path=self.bmv2_exe,
            json_path=self.switch_json,
            log_console=True,
            pcap_dump=self.pcap_dir,
        )

        self.topo = ExerciseTopo(
            self.hosts,
            self.switches,
            self.links,
            self.log_dir,
            self.bmv2_exe,
            self.pcap_dir,
        )

        self.net = Mininet(
            topo=self.topo,
            link=TCLink,
            host=P4Host,
            switch=defaultSwitchClass,
            controller=None,
        )

    def program_switch_p4runtime(self, sw_name, sw_dict):
        """This method will use P4Runtime to program the switch using the
        content of the runtime JSON file as input.
        """
        sw_obj = self.net.get(sw_name)
        grpc_port = sw_obj.grpc_port
        device_id = sw_obj.device_id
        runtime_json = sw_dict["runtime_json"]
        logging.info(
            "Configuring switch %s using P4Runtime with file %s"
            % (sw_name, runtime_json)
        )
        with open(runtime_json, "r") as sw_conf_file:
            outfile = "%s/%s-p4runtime-requests.txt" % (self.log_dir, sw_name)
            p4runtime_lib.simple_controller.program_switch(
                addr="127.0.0.1:%d" % grpc_port,
                device_id=device_id,
                sw_conf_file=sw_conf_file,
                workdir=os.getcwd(),
                proto_dump_fpath=outfile,
                runtime_json=runtime_json,
            )

    def program_switch_cli(self, sw_name, sw_dict):
        """This method will start up the CLI and use the contents of the
        command files as input.
        """
        cli = "simple_switch_CLI"
        # get the port for this particular switch's thrift server
        sw_obj = self.net.get(sw_name)
        thrift_port = sw_obj.thrift_port

        cli_input_commands = sw_dict["cli_input"]
        logging.info(
            "Configuring switch %s with file %s" % (sw_name, cli_input_commands)
        )
        with open(cli_input_commands, "r") as fin:
            cli_outfile = "%s/%s_cli_output.log" % (self.log_dir, sw_name)
            with open(cli_outfile, "w") as fout:
                subprocess.Popen(
                    [cli, "--thrift-port", str(thrift_port)], stdin=fin, stdout=fout
                )

    def program_switches(self):
        """This method will program each switch using the BMv2 CLI and/or
        P4Runtime, depending if any command or runtime JSON files were
        provided for the switches.
        """
        for sw_name, sw_dict in self.switches.items():
            if "cli_input" in sw_dict:
                self.program_switch_cli(sw_name, sw_dict)
            if "runtime_json" in sw_dict:
                self.program_switch_p4runtime(sw_name, sw_dict)

    def program_hosts(self):
        """Execute any commands provided in the topology.json file on each Mininet host"""
        for host_name, host_info in list(self.hosts.items()):
            h = self.net.get(host_name)
            if "commands" in host_info:
                for cmd in host_info["commands"]:
                    h.cmd(cmd)

    def do_net_cli(self):
        """Starts up the mininet CLI and prints some helpful output.

        Assumes:
            - A mininet instance is stored as self.net and self.net.start() has
              been called.
        """
        for s in self.net.switches:
            s.describe()
        for h in self.net.hosts:
            h.describe()
        logging.info("Starting mininet CLI")
        # Generate a message that will be printed by the Mininet CLI to make
        # interacting with the simple switch a little easier.
        print("")
        print("======================================================================")
        print("Welcome to the BMV2 Mininet CLI!")
        print("======================================================================")
        print("Your P4 program is installed into the BMV2 software switch")
        print("and your initial runtime configuration is loaded. You can interact")
        print("with the network using the mininet CLI below.")
        print("")
        if self.switch_json:
            print("To inspect or change the switch configuration, connect to")
            print("its CLI from your host operating system using this command:")
            print("  simple_switch_CLI --thrift-port <switch thrift port>")
            print("")
        print("To view a switch log, run this command from your host OS:")
        print("  tail -f %s/<switchname>.log" % self.log_dir)
        print("")
        print(
            "To view the switch output pcap, check the pcap files in %s:"
            % self.pcap_dir
        )
        print(" for example run:  sudo tcpdump -xxx -r s1-eth1.pcap")
        print("")
        if "grpc" in self.bmv2_exe:
            print("To view the P4Runtime requests sent to the switch, check the")
            print("corresponding txt file in %s:" % self.log_dir)
            print(" for example run:  cat %s/s1-p4runtime-requests.txt" % self.log_dir)
            print("")

        CLI(self.net)


class TestSender:
    def __init__(self, exercise_runner, testcases_file, switches, log_dir):
        """Reads the testcases and paths from the given file and initializes the paramters accordingly.

        Arguments:
            exercise_runner : object  // A python object that gives access to the running mininet instance
            testcases_file : string   // A json file which describes the testcases
            switches : string         // A dictionary with the switch name as key and a dictionary with switch information as value
            log_dir  : string         // Path to a directory for storing test logs
        """

        logging.info("Reading testcases from file")
        with open(testcases_file, "r+") as f:
            test_defintion = json.load(f)
            # ensure each test has a unique identifier
            id_missing = False
            for test in test_defintion["testcases"]:
                if "id" not in test:
                    id_missing = True
                    test["id"] = str(uuid.uuid1())
            # add generated identifiers to the testcases definition
            if id_missing:
                logging.warning(
                    "Found tests with no ID going to update testcase definition"
                )
                f.seek(0)
                json.dump(test_defintion, f, indent=2)
                f.truncate()
            self.testcases = test_defintion["testcases"]
            self.paths = testing.utils.get_path_dict(testcases_file)
        # ensure all the needed directories exist and are directories
        for dir_name in [log_dir]:
            if not os.path.isdir(dir_name):
                if os.path.exists(dir_name):
                    raise Exception("'%s' exists and is not a directory!" % dir_name)
                os.mkdir(dir_name)
        self.log_dir = log_dir
        self.switches = switches
        self.exercise_runner = exercise_runner

    def reset_bmv2_control_plane(self):
        reset_required = False
        cwd = os.getcwd()
        for sw_name, sw_dict in self.switches.items():
            # determine the paths of the runtime files of the specific switch
            runtime_path = os.path.join(cwd, sw_dict["runtime_json"])
            backup_runtime_path = os.path.join(cwd, f"{sw_dict['runtime_json']}.bak")
            # check if a backup control plane file exists (if yes the configuration of that switch was changed)
            if os.path.isfile(backup_runtime_path):
                logging.info("Found that the configuration of %s was changed", sw_name)
                os.rename(backup_runtime_path, runtime_path)
                reset_required = True
        # reset all switches with the default control plane if a backup file was found
        if reset_required:
            logging.info(
                "Reprogramming switches to reset BMv2 control plane configuration to default"
            )
            self.exercise_runner.program_switches()
        else:
            logging.info(
                "Skipping switch reporgramming --> configuration state already satisfied"
            )

    def patch_bmv2_control_plane(self, patch):
        cwd = os.getcwd()
        # apply the patch on all target swtiches
        for sw in patch["switches"]:
            logging.info("Patching %s (table: %s)", sw, patch["table"])
            # determine the paths of the runtime files of the specific switch
            runtime_path = os.path.join(cwd, self.switches[sw]["runtime_json"])
            backup_runtime_path = os.path.join(
                cwd, f"{self.switches[sw]['runtime_json']}.bak"
            )
            # copy the original runtime to a backup file if not already done (used for later restore)
            if not os.path.isfile(backup_runtime_path):
                copy(runtime_path, backup_runtime_path)
            with open(runtime_path, "r+") as f:
                runtime_defintion = json.load(f)
                # find matching table entry in runtime
                for entry in runtime_defintion["table_entries"]:
                    if entry["table"] == patch["table"]:
                        table = entry
                # validate the action name (only continue if the action names match)
                if table["action_name"] != patch["action"]:
                    raise ValueError(f"Invalid action name: {patch['action']}")
                action_params = table["action_params"]
                # apply patches
                for params in patch["parameters"]:
                    for param_name, param_value in params.items():
                        action_params[param_name] = param_value
                f.seek(0)
                json.dump(runtime_defintion, f, indent=2)
                f.truncate()

    def copy_tmp_runtimes(self, test):
        # create directories for test specific runtime definitions
        cwd = os.getcwd()
        tmp_runtime_dir = os.path.join(cwd, "dev-network/tmp_runtimes")
        test_runtime_dir = os.path.join(tmp_runtime_dir, test["id"])
        os.makedirs(test_runtime_dir, exist_ok=True)
        # copy the runtime definitions of each switch on the path to the specific tmp runtime directory
        path = self.paths[test["path"]]
        for sw in path["nodes"]:
            logging.info(
                "Copying runtime of %s (id: %s)",
                sw["name"],
                test["id"],
            )
            copy(
                self.switches[sw["name"]]["runtime_json"],
                os.path.join(test_runtime_dir, f"{sw['name']}-runtime.json"),
            )

    def send_test_data(self, test):
        self.copy_tmp_runtimes(test)
        path = self.paths[test["path"]]
        logging.info(
            "Sending test data from %s to %s (id: %s)",
            path["src"],
            path["dst"],
            test["id"],
        )
        # run the send.py script on the sending host and send the specified number of packets over the network
        if test["protocol"] == "ipv6":
            host = self.exercise_runner.net.get(path["src"])
            host.cmd(
                f'python3 ./dev-network/utils/testing/send.py --src {path["src"]} --dst {path["dst"]} --count {test["num_packets"]} --ipv6'
            )


def get_args():
    cwd = os.getcwd()
    default_logs = os.path.join(cwd, "logs")
    default_pcaps = os.path.join(cwd, "pcaps")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--quiet",
        help="Suppress log messages.",
        action="store_true",
        required=False,
        default=False,
    )
    parser.add_argument(
        "-t",
        "--topo",
        help="Path to topology json",
        type=str,
        required=False,
        default="./topology.json",
    )
    parser.add_argument(
        "-l", "--log-dir", type=str, required=False, default=default_logs
    )
    parser.add_argument(
        "-p", "--pcap-dir", type=str, required=False, default=default_pcaps
    )
    parser.add_argument("-j", "--switch_json", type=str, required=False)
    parser.add_argument(
        "-b",
        "--behavioral-exe",
        help="Path to behavioral executable",
        type=str,
        required=False,
        default="simple_switch",
    )
    parser.add_argument(
        "--testcases",
        help="Path to testcase defintion file",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--test",
        help="Boolean flag to indicate that tests shall be run",
        required=False,
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--demo",
        help="Boolean flag to indicate that demo shall be run",
        required=False,
        default=False,
        action="store_true",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    # configure logging
    cwd = os.getcwd()
    test_log_dir = os.path.join(cwd, f"{args.log_dir}")
    os.makedirs(test_log_dir, exist_ok=True)
    if args.demo:
        logging.basicConfig(
            format="%(asctime)s:%(levelname)s:%(message)s",
            level=logging.INFO,
        )
    else:
        logging.basicConfig(
            filename=f"{test_log_dir}/h1-test-sender.log",
            format="%(asctime)s:%(levelname)s:%(message)s",
            level=logging.INFO,
        )

    logging.info(
        "TEST RUN STARTED (please wait this might take a few seconds)",
    )

    # instantiate exercise runner
    exercise = ExerciseRunner(
        args.topo,
        args.log_dir,
        args.pcap_dir,
        args.switch_json,
        args.behavioral_exe,
        args.quiet,
    )
    exercise.run_exercise()
    # instantiate test_sender
    test_sender = TestSender(exercise, args.testcases, exercise.switches, args.log_dir)
    # start listener on all destination hosts
    receiver_hosts = testing.utils.get_path_destinations(test_sender.paths)
    for host in receiver_hosts:
        h = exercise.net.get(host)
        if args.test:
            h.cmd(
                f"python3 {cwd}/dev-network/utils/run_test_receiver.py --host {host} --log-dir {args.log_dir} --testcases {args.testcases} &"
            )
        elif args.demo:
            h.cmd(
                f"python3 {cwd}/dev-network/utils/run_test_receiver.py --host {host} --log-dir {args.log_dir} --testcases {args.testcases} --export &"
            )
    # send traffic for each testcase
    for test in test_sender.testcases:
        logging.info("Preparing for: %s (id: %s)", test["name"], test["id"])
        sleep(2)
        # patch the bmv2 control plane if parameter patches are defined
        if (
            "ioam_aggregation" in test
            and "parameter_patches" in test["ioam_aggregation"]
        ):
            for patch in test["ioam_aggregation"]["parameter_patches"]:
                test_sender.patch_bmv2_control_plane(patch)
            logging.info(
                "Reprogramming switches to apply the patched BMv2 control plane configuration"
            )
            exercise.program_switches()
            test_sender.send_test_data(test)
            test_sender.reset_bmv2_control_plane()
        else:
            test_sender.send_test_data(test)
        if args.demo and 'stop' in test and test['stop']:
            input("Press enter to continue with the demo...")
    logging.info("Shutting down environment")
    # Wait a short amount of time to let the receivers complete their validation and data export
    sleep(3)
    logging.info(
        "TEST RUN COMPLETED (detailed logs about the results are located at: %s)",
        test_log_dir,
    )
    exercise.net.stop()
