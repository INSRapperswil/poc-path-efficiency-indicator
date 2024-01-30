control process_ioam_tracing(inout headers hdr,
                             inout metadata meta,
                             inout standard_metadata_t standard_metadata) {

    action ioam_trace_push() {
        hdr.ioam_t_ipv6_option.setValid();
        hdr.ioam_t_ioam.setValid();
        hdr.ioam_t_ioam_trace.setValid();

        // Initialize Option
        hdr.ioam_t_ipv6_option.optionType = IOAM_OPTION_TYPE_CHG;
        hdr.ioam_t_ipv6_option.optionDataLen = IOAM_TRACE_OPTION_DATA_LEN;

        // Initialize IOAM Header
        hdr.ioam_t_ioam.reserved = 0;
        hdr.ioam_t_ioam.ioamOptType = IOAM_PRE_ALLOC_TRACE_OPTION_TYPE;

        // Initialize IOAM Trace Option Type Header
        hdr.ioam_t_ioam_trace.namespaceID = 0;
        hdr.ioam_t_ioam_trace.nodeLen = 1; // num of 4 octet units
        hdr.ioam_t_ioam_trace.flags = 0;
        hdr.ioam_t_ioam_trace.remainingLen = (bit<7>) IOAM_TRACE_NUM_NODES; // num of 4 octet units
        hdr.ioam_t_ioam_trace.ioamTraceType = 0x800000; // MSB set to 1
        hdr.ioam_t_ioam_trace.reserved = 0;
        hdr.ioam_t_ioam_trace.dataList = 0;
    }

    action ioam_trace_node(ioamNodeID_t nodeID){
        // node_data_field: | hop limit (8 Bit) | node id (24 Bit) |
        bit<(IOAM_TRACE_DATA_LIST_LEN)> node_data_field = (bit<(IOAM_TRACE_DATA_LIST_LEN)>) nodeID;

        // generate hop limit 32 bit mask --> 8 MSB set to the hop limit of IPv6 header at egress
        bit<(IOAM_TRACE_DATA_LIST_LEN)> hop_limit_mask = (bit<(IOAM_TRACE_DATA_LIST_LEN)>) (hdr.ipv6.hopLimit) << 24;

        // append the hop limit as the 8 MSB of the node data field
        node_data_field =  node_data_field | hop_limit_mask;

        // push data field to node data stack
        hdr.ioam_t_ioam_trace.dataList = hdr.ioam_t_ioam_trace.dataList << 32;
        hdr.ioam_t_ioam_trace.dataList = hdr.ioam_t_ioam_trace.dataList | node_data_field;

        // decrement remaining length
        hdr.ioam_t_ioam_trace.remainingLen = hdr.ioam_t_ioam_trace.remainingLen - 1;
    }

    table ioam_trace_node_exact {
        key = {
            hdr.ethernet.srcAddr: exact;
        }
        actions = {
            ioam_trace_node;
            NoAction;
        }
        size = 1;
    }

    apply {
        if (!hdr.ioam_t_ioam_trace.isValid()) {
            ioam_trace_push();
        }
        if (hdr.ioam_t_ioam_trace.remainingLen > 0) {
            // add node id and hop count to array
            ioam_trace_node_exact.apply();
        } else {
            // set overflow bit
            hdr.ioam_t_ioam_trace.flags = hdr.ioam_t_ioam_trace.flags | 0x8;
        }
    }
}