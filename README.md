# Proof-of-Concept: Path Efficiency Indicator in Computer Networks

**Visibility, a first step towards sustainable networking.**

## Project Overview

This research project, which started with our semester thesis, is based on the collaboration between the Eastern Switzerland University of Applied Sciences (OST) and Alexander Clemm from Sympotech, working closely together with the Internet Engineering Task Force (IETF).
The project is part of broad-based research work done at IETF and focuses on a specific sub-area in the field of Green Networking Metrics.

The project is mainly related to the RFC documents and drafts below.

- [Green Networking Metrics (Draft)](https://www.ietf.org/archive/id/draft-cx-green-metrics-00.html): Defines the underlying research field
- [IOAM Aggregation Trace Option Type (Draft)](https://www.ietf.org/archive/id/draft-cxx-ippm-ioamaggr-00.html): Defines the method used to store the PEI or min/max HEI values in the user packet header data
- [IOAM Data Fields (RFC9197)](https://www.rfc-editor.org/rfc/rfc9197.html): Defines the IOAM Trace Option type which is used to trace the path a packet traverses
- [Internet Protocol, Version 6 (IPv6) (RFC2460)](https://www.rfc-editor.org/rfc/rfc2460): Defines the Hop by Hop Extension header which is used to encapsulate the IOAM data

### Members

The people involved are:

- **Bachelor Students:**
  - Ramon Bister
  - Reto Furrer
- **Advisor:** Prof. Laurent Metzger (OST)
- **Co-Advisor:** Severin Dellsperger (OST)
- **External Partner:** Alexander Clemm (Sympotech)

### Situation

Recognizing climate change's urgency and the need to reduce greenhouse emissions, governments and the United Nations are emphasizing the importance of lowering carbon footprints across industries, including the networking sector.
This sustainability shift is driven by both economic incentives and corporate responsibility.
Network providers are increasingly considering measures like making hardware more energy-efficient and optimizing routing and virtual networking functions.
Exploring green networking metrics for paths could create new opportunities to minimize carbon footprints and steer traffic along eco-friendly paths.
**Although collecting network telemetry has gained attention, existing standards like IOAM and INT have not yet incorporated green metrics, hindering data aggregation.**

### Goals

The main objective of this research project is to propose a practical solution on how to aggregate, transport and interpret green metrics within a simulated computer network.

## Getting Started

The following sections will give you a quick overview about the structure of the reposiotry.
Additionally a guide is given on how to setup your own development environment in order to test the PoC implementation your own.

### Repository Overview

- **dev-network:** Directory containing:
  - Mininet topology definition
  - Static control plane definitions of the BMv2 porgrammable targets
  - Python utilities to bootstrap the Mininet lab environment
  - Resource definition to customize the network topology and adjust component values (inside *jinja2/resources*)
- **includes:** Directory containing the P4 source included by the main.p4 file
- **main.p4** Main P4 source file which defines the forwarding pipeline of the BMv2 targets in order to collect the path efficiency indicator

Most of the utilities used are from [P4lang Tutorials](https://github.com/p4lang/tutorials) and slightly modified to fit our needs.

### Development Environment Installation

In order to run the PoC the following software needs to be installed

- Mininet
- BMv2
- P4 Compiler
- Python Scapy

#### Option 1: Use the virtual machine provided by P4lang

In order to get the virtual machine provided by P4lang refer to: https://github.com/p4lang/tutorials

#### Option 2: Setup your own virtual machine

The installation procedure documented below was tested on an Ubuntu 23.04 virtual machine.

##### Install Dependencies

Some of the installation steps require _curl_ to be installed.
Curl is available from the standard Ubuntu apt repository and can be installed with the _apt-get install_ command.

```sh
sudo apt-get install curl
```

#### Install Mininet

Mininet is available from the standard Ubuntu apt repository and can be installed with the _apt-get install_ command.

```sh
sudo apt-get install mininet
```

#### Install BMv2

The BMv2 software switches are not available in the standard Ubuntu apt repository but after adding the p4lang repository to the apt sources the required software can be installed with the _apt-get install_ command.

```sh
source /etc/os-release
echo "deb http://download.opensuse.org/repositories/home:/p4lang/xUbuntu_${VERSION_ID}/ /" | sudo tee /etc/apt/sources.list.d/home:p4lang.list
curl -fsSL "https://download.opensuse.org/repositories/home:p4lang/xUbuntu_${VERSION_ID}/Release.key" | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/home_p4lang.gpg > /dev/null
sudo apt update
sudo apt install p4lang-bmv2
```

#### Install P4 Compiler (p4c)

The P4 compiler is not available in the standard Ubuntu apt repository but after adding the p4lang repository to the apt sources the required software can be installed with the _apt-get install_ command.

```sh
source /etc/lsb-release
echo "deb http://download.opensuse.org/repositories/home:/p4lang/xUbuntu_${DISTRIB_RELEASE}/" | sudo tee /etc/apt/sources.list.d/home:p4lang.list
curl -fsSL https://download.opensuse.org/repositories/home:p4lang/xUbuntu_${DISTRIB_RELEASE}/Release.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/home_p4lang.gpg > /dev/null
sudo apt-get update
sudo apt install p4lang-p4c
```

#### Install Python Dependencies

The python library scapy is used to send test traffic over the network.
Install scapy using the following command.

```sh
sudo apt-get install python3-scapy
```

### Resource Definition

Optionally you have the possibility to adjust the topology and configuration parameters of the test network.
The resources are defined in *dev-network/utils/jinja2/resources/resources.yaml* in YAML format.

You may define the parameters for the following objects.

**To apply your changes in the resources file make sure to run `make config` before you start the test network.**

#### Path Definition

The network does not use a routing protocol.
Therefore all routes are specified statically.
Use the following format to define paths between hosts.

```yaml
paths:
  - from: h1
    to: h2
    via: [s1, s2, s4]
    return_route: true
```

With return route set to true a symmetric route will be setup in the oposite direction.

#### Host Definition

Hosts can be configured as follows.
The commands specified are executed on host startup.

```yaml
hosts:
  h1:
    ipv4:
      ip: 10.100.0.10
      net: 10.100.0.0
      prefix_len: 24
    ipv6:
      ip: 2001:DB8:64::10
      net: "2001:DB8:64::"
      prefix_len: 64
    mac: 08:00:00:10:00:10
    commands:
      - "route add default gw 10.100.0.1 dev eth0"
      - "arp -i eth0 -s 10.100.0.1 08:00:00:00:01:00"
      - "python3 ./dev-network/utils/traffic_generator.py --ipv6 --src 'h1' --infinite --startup-delay 15 --logfile &"
```

#### Switch Definition

Switches can be configured as follows.
To adjust the energy metric of a switch you may adjust the hei (Hop Efficiency Indicator) value or modify the lei (Link Efficiency Indicator) value inside the port definitions.

```yaml
switches:
  s1:
    mac: 08:00:00:00:01:00
    hei:
      - data_param: 255
        value: 10000
    ioam:
      namespace_id: 10
      node_id: 1
      aggregators: # 1 = SUM / 2 = MIN / 4 = MAX
        - 1 # selected if last two bits of payload size are [00]
        - 2 # selected if last two bits of payload size are [01]
        - 1 # selected if last two bits of payload size are [10]
        - 4 # selected if last two bits of payload size are [11]
      data_param: 255
    ports:
      1:
        neighbor: s2
        lei: 10
      2: 
        neighbor: s3
        lei: 20
      3:
        neighbor: h1
        lei: 30
```


### Run PoC

To start and stop the test network with the BMv2 targets programmed with the current version of the P4 application the _make_ command can be used.

```sh
# (optional) generate the configurations (only needed in case the resources file was modified)
make config
# start test network
make run
# stop test network (when inside the mininet console enter exit instead)
make stop
# remove all generated files (incl. configurations)
make clean
```

#### Traffic Generation

Using the default configuration all hosts start to send traffic to randomly selected destination hosts after a delay of 15 seconds.
In case you would like to disable the automatic traffic generation remove the following lines from all commands sections in the host definition in the resources yaml file.

```sh
python3 ./dev-network/utils/traffic_generator.py <-- details omitted -->
```

To send traffic manually e.g. from h1 to h2 you can execute the traffic generator utility manually within the mininet console using the following command.

```sh
h1 python3 ./dev-network/utils/traffic_generator.py --src "h1" --dst "h2"
```

#### Wireshark Captures

All traffic sent via the test network is written to pcap files located in the *pcaps* directory.
The directory contains the captures of all switches divided by interface and transmission direction.
For example to view traffic which was sent via port 3 of switch 4 open the file *s4-eth3_out.pcap*.