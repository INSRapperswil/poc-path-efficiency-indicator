# Proof-of-Concept: Path Efficiency Indicator in Computer Networks

**Visibility, a first step towards sustainable networking.**

## Project Overview

This research project, which started with our semester thesis, is based on the collaboration between the Eastern Switzerland University of Applied Sciences (OST) and Alexander Clemm, Futurewei Technologies, Inc. working closely together with the Internet Engineering Task Force (IETF).
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
- **External Partner:** Alexander Clemm (Futurewei Technologies, Inc.)

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
  - Python utilities to bootstrap the Mininet lab environment, to execute the test and the demo
- **includes:** Directory containing the P4 source included by the main.p4 file
- **main.p4** Main P4 source file which defines the forwarding pipeline of the BMv2 targets in order to collect the path efficiency indicator
- **run_demo.sh** Script called by the Makefile to run the demonstration
- **run_tests.sh** Script called by the Makefile to run the tests

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

### Run PoC

To start and stop the development network with the BMv2 targets programmed with the current version of the P4 application the _make_ command can be used.

```sh
# start development network
make run
# stop the development network
make stop
# run automated tests
make test
# run automated demos
make demo
```

#### Manual Interaction using make run

1. Start the environment using _make run_
2. Send traffic from one host to another

- In order to send 1 packet from h1 to h2 invoke the send.py utility on h1 using the following command wihtin the interactive mininet shell

```sh
h1 python3 ./dev-network/utils/testing/send.py --src "h1" --dst "h2" --count 1 --ipv6
```

3. Checkout the wireshark captures located in the _pcaps_ folder.

#### Run Tests

Use the _make test_ command to run the test cases sepcified in _dev-network/test/cases.json_

You should receive a similar output than the one below:

```
2024-01-30 10:17:50,254:INFO:TEST RUN STARTED (please wait this might take a few seconds)
2024-01-30 10:17:58,695:INFO:TEST PASSED (id: 4be8d9aa-8c75-11ee-99de-0800270cf606)
2024-01-30 10:18:01,214:INFO:TEST PASSED (id: 4be8d9ab-8c75-11ee-99de-0800270cf606)
2024-01-30 10:18:03,792:INFO:TEST PASSED (id: 4be8d9ac-8c75-11ee-99de-0800270cf606)
2024-01-30 10:18:06,503:INFO:TEST PASSED (id: 4be8d9ad-8c75-11ee-99de-0800270cf606)
2024-01-30 10:18:09,275:INFO:TEST PASSED (id: 604e1b4e-95d5-11ee-85ca-0800270cf606)
2024-01-30 10:18:12,042:INFO:TEST PASSED (id: 77ddef58-8cfe-11ee-99de-0800270cf606)
2024-01-30 10:18:14,807:INFO:TEST PASSED (id: a1c6a122-8d01-11ee-99de-0800270cf606)
2024-01-30 10:18:18,025:INFO:TEST RUN COMPLETED (detailed logs about the results are located at: /home/user/git/poc-path-efficiency-indicator/logs/testing/20240130101750)
```

#### Run the Demo

Use the _make demo_ command to run the demo cases sepcified in _dev-network/demo/cases.json_
Once the command execution completed open the Jupyter Notebook at _dev-network/utils/demo.ipynb_ and press run all cells.
