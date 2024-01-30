control process_ipv6_ext_header_init(inout headers hdr,
                                     inout metadata meta,
                                     inout standard_metadata_t standard_metadata) {
    action init_ipv6_ext_hop_by_hop() {
        // Set the added headers to be valid
        hdr.ipv6_ext_hop_by_hop.setValid();

        // Initialize IPv6 Hop by Hop Extension Header
        hdr.ipv6_ext_hop_by_hop.nextHeader = hdr.ipv6.nextHeader;
        hdr.ipv6_ext_hop_by_hop.hdrLen = 1 + IOAM_TRACE_NUM_NODES / 2 + 3; // 1 octet unit for the header metadata + num nodes / 2 (1 node entry requires 4 octet units) + 3 octet units for IOAM Aggregation

        // Add Hop by Hop extension header to linked list
        hdr.ipv6.nextHeader = IPV6_NH_HOP_BY_HOP;
        hdr.ipv6.payloadLen = hdr.ipv6.payloadLen + 16 + (bit<16>) IOAM_TRACE_NUM_NODES * 4 + 24; // current payload + IOAM metadata + node data list length + IOAM Aggregation Data (18 Byte) + 6 Byte Padding
    }
    apply {
        if (!hdr.ipv6_ext_hop_by_hop.isValid()) {
            init_ipv6_ext_hop_by_hop();
        }
    }
}