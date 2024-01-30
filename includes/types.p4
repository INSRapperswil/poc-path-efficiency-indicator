/*************************************************************************
*********************** TYPE ALIAS  **************************************
*************************************************************************/

typedef bit<9>  egressSpec_t;

// Ethernet Types
typedef bit<48> macAddr_t;

// IP Types
typedef bit<32> ip4Addr_t;
typedef bit<128> ip6Addr_t;

// IOAM Types
typedef bit<24> ioamNodeID_t;
typedef bit<8> ioamAggregator_t;
typedef bit<32> ioamAggregate_t;

struct ioamAggrMeta_t {
    ioamAggregate_t aggregate;
    ioamNodeID_t nodeID;
}

// UDP Types
typedef bit<16> udpAddr_t;

// Efficiency Indicator Types
typedef bit<1> inverse_t;
typedef bit<2> weight_t;
typedef bit<32> parameter_t;
typedef bit<5> parameterSize_t;
typedef bit<16> component_t;
typedef bit<15> normValue_t;

typedef bit<7> energyMix_t;
typedef bit<10> idlePower_t;
typedef bit<16> embeddedCarbon_t;
