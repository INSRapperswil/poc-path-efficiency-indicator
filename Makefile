BUILD_DIR = build
PCAP_DIR = pcaps
LOG_DIR = logs
CONFIG_GEN_DIR = dev-network/utils/jinja2

BMV2_SWITCH_EXE = simple_switch_grpc
TOPO = dev-network/topology.json
RESOURCES_FILE_NAME = resources.yaml

P4C = p4c-bm2-ss
P4C_ARGS += --p4runtime-files $(BUILD_DIR)/$(basename $@).p4.p4info.txt --emit-externs

BMV2_REPO = ${HOME}/git/ba/behavioral-model
BMV2_EXTERN_DIR = ${BMV2_REPO}/externs/obj
BMV2_EXTERNS = ${BMV2_EXTERN_DIR}/ipfix.so # comma separated list

CONFIG_GEN_SCRIPT = $(CONFIG_GEN_DIR)/main.py
RUN_SCRIPT = dev-network/utils/run_exercise.py

ifndef TOPO
TOPO = topology.json
endif

source = $(wildcard *.p4)
compiled_json := $(source:.p4=.json)

ifndef DEFAULT_PROG
DEFAULT_PROG = $(wildcard *.p4)
endif
DEFAULT_JSON = $(BUILD_DIR)/$(DEFAULT_PROG:.p4=.json)

# Define NO_P4 to start BMv2 without a program
ifndef NO_P4
run_args += -j $(DEFAULT_JSON)
endif

# Set BMV2_SWITCH_EXE to override the BMv2 target
ifdef BMV2_SWITCH_EXE
run_args += -b $(BMV2_SWITCH_EXE)
endif

# Set BMV2_EXTERNS to define BMV2 modules (shared libraries)
ifdef BMV2_EXTERNS
run_args += -m $(BMV2_EXTERNS)
endif

all: run

config:
	python3 $(CONFIG_GEN_SCRIPT) \
	--template-dir $(CONFIG_GEN_DIR)/templates \
	--mininet-template-name mininet_topology.j2 \
	--bmv2-template-name bmv2_runtime.j2 \
	--resources $(CONFIG_GEN_DIR)/resources/$(RESOURCES_FILE_NAME) \
	--log-dir $(LOG_DIR) \
	--out-dir dev-network/

run: build
	sudo python3 $(RUN_SCRIPT) -t $(TOPO) $(run_args)

stop:
	sudo mn -c

build: dirs $(compiled_json)

%.json: %.p4
	$(P4C) --p4v 16 $(P4C_ARGS) -o $(BUILD_DIR)/$@ $<

dirs:
	mkdir -p $(BUILD_DIR) $(PCAP_DIR) $(LOG_DIR)

clean: stop
	rm -f *.pcap
	rm -rf $(BUILD_DIR) $(PCAP_DIR) $(LOG_DIR)
	rm -f ${TOPO}
	rm -f dev-network/*-runtime.json
	rm -f dev-network/traffic-generator-config.json
