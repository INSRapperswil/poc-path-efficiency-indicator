control process_ioam_aggregation(inout headers hdr,
                                     inout metadata meta,
                                     inout standard_metadata_t standard_metadata) {

    action ioam_aggr_push(ioamAggregator_t aggregator) {
        // Set the added headers to be valid
        hdr.ioam_a_ipv6_option.setValid();
        hdr.ioam_a_ioam.setValid();
        hdr.ioam_a_ioam_aggregation.setValid();
        hdr.option_padn.setValid();
        hdr.option_padn_data.setValid();

        // Initialize Option
        hdr.ioam_a_ipv6_option.optionType = IOAM_OPTION_TYPE_CHG;
        hdr.ioam_a_ipv6_option.optionDataLen = IOAM_AGGREGATION_OPTION_DATA_LEN;

        // Initialize IOAM Header
        hdr.ioam_a_ioam.reserved = 0;
        hdr.ioam_a_ioam.ioamOptType = IOAM_AGGREGATION_OPTION_TYPE;

        // Initialize IOAM Aggregation Type Header
        hdr.ioam_a_ioam_aggregation.namespaceID = 0;
        hdr.ioam_a_ioam_aggregation.flags = 0;
        hdr.ioam_a_ioam_aggregation.reserved = 0;
        hdr.ioam_a_ioam_aggregation.dataParam = 0xFF;
        hdr.ioam_a_ioam_aggregation.aggregator = aggregator;
        hdr.ioam_a_ioam_aggregation.aggregate = meta.ioamAggrMeta.aggregate;
        hdr.ioam_a_ioam_aggregation.auxilDataNodeID = meta.ioamAggrMeta.nodeID;
        hdr.ioam_a_ioam_aggregation.hopCount = 1;

        // Set PadN Option add 4 Bytes padding
        hdr.option_padn.optionType = 1;
        hdr.option_padn.optionDataLen = IPV6_EXT_HOP_BY_HOP_PADDING - 2; // N - 2 | N=2 => 0
        hdr.option_padn_data.padding = 0;
    }

    action ioam_aggr_sum() {
        hdr.ioam_a_ioam_aggregation.hopCount = hdr.ioam_a_ioam_aggregation.hopCount + 1;
        hdr.ioam_a_ioam_aggregation.aggregate = hdr.ioam_a_ioam_aggregation.aggregate + meta.ioamAggrMeta.aggregate;
        hdr.ioam_a_ioam_aggregation.auxilDataNodeID = meta.ioamAggrMeta.nodeID;
    }

    action ioam_aggr_min() {
        hdr.ioam_a_ioam_aggregation.hopCount = hdr.ioam_a_ioam_aggregation.hopCount + 1;
        if (hdr.ioam_a_ioam_aggregation.aggregate > meta.ioamAggrMeta.aggregate) {
            hdr.ioam_a_ioam_aggregation.aggregate = meta.ioamAggrMeta.aggregate;
            hdr.ioam_a_ioam_aggregation.auxilDataNodeID = meta.ioamAggrMeta.nodeID;
        }
    }

    action ioam_aggr_max() {
        hdr.ioam_a_ioam_aggregation.hopCount = hdr.ioam_a_ioam_aggregation.hopCount + 1;
        if (hdr.ioam_a_ioam_aggregation.aggregate < meta.ioamAggrMeta.aggregate) {
            hdr.ioam_a_ioam_aggregation.aggregate = meta.ioamAggrMeta.aggregate;
            hdr.ioam_a_ioam_aggregation.auxilDataNodeID = meta.ioamAggrMeta.nodeID;
        }
    }

    action get_node_id(ioamNodeID_t nodeID) {
        meta.ioamAggrMeta.nodeID = nodeID;
    }

    table ioam_aggr_push_exact {
        key = {
            hdr.ethernet.srcAddr: exact;
        }
        actions = {
            ioam_aggr_push;
            NoAction;
        }
        size = 1;
    }

    table node_id {
        key = {
            hdr.ethernet.srcAddr: exact;
        }
        actions = {
            get_node_id;
            NoAction;
        }
        size = 1;
    }

    apply {
        node_id.apply();
        if (hdr.ioam_a_ioam_aggregation.isValid()) {
            switch (hdr.ioam_a_ioam_aggregation.aggregator) {
                IOAM_AGGREGATOR_SUM: {ioam_aggr_sum();}
                IOAM_AGGREGATOR_MIN: {ioam_aggr_min();}
                IOAM_AGGREGATOR_MAX: {ioam_aggr_max();}
            }
        } else {
            ioam_aggr_push_exact.apply();
        }
    }
}