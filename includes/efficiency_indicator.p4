/*************************************************************************
***************** E F F I C I E N C Y  I N D I C A T O R  ****************
*************************************************************************/

control process_efficiency_indicator(inout headers hdr,
                                     inout metadata meta,
                                     inout standard_metadata_t standard_metadata) {
    action drop() {
        mark_to_drop(standard_metadata);
    }

    action calc_carbon_metric_parameter(parameter_t parameter, parameterSize_t parameterSize, weight_t weight, inverse_t inverse) {
        // Normalization
        normValue_t normValue = 0;
        if(parameterSize < normValue_t.minSizeInBits()) {
            normValue = (normValue_t)parameter << (normValue_t.minSizeInBits() - parameterSize);
        } else if(parameterSize > normValue_t.minSizeInBits()){
            parameter_t tempNormValue = parameter >> (parameterSize - normValue_t.minSizeInBits());
            normValue = (normValue_t)tempNormValue;
        }

        // Inversion
        if(inverse == 1) {
            normValue = MAX_VALUE_15_BIT - normValue;
        }

        // Weighting normValue
        component_t component = 0;
        if(weight == 2) {
            component = (component_t)normValue << 1;
        } else if(weight == 1) {
            component = (component_t)normValue;
        } else if(weight == 0) {
            component = (component_t)normValue >> 1;
        }

        // Add component to HEI value
        meta.ioamAggrMeta.aggregate = meta.ioamAggrMeta.aggregate + (ioamAggregate_t)component;
    }

    action get_carbon_metric_energy_mix(energyMix_t value, weight_t weight, inverse_t inverse) {
        calc_carbon_metric_parameter((parameter_t)value, value.minSizeInBits(), weight, inverse);
    }

    action get_carbon_metric_idle_power(idlePower_t value, weight_t weight, inverse_t inverse) {
        calc_carbon_metric_parameter((parameter_t)value, value.minSizeInBits(), weight, inverse);
    }

    action get_carbon_metric_embedded_carbon(embeddedCarbon_t value, weight_t weight, inverse_t inverse) {
        calc_carbon_metric_parameter((parameter_t)value, value.minSizeInBits(), weight, inverse);
    }

    table carbon_metric_component_energy_mix {
        key = {
            hdr.ethernet.srcAddr: exact;
        }
        actions = {
            get_carbon_metric_energy_mix;
            drop;
            NoAction;
        }
        size = 1;
        default_action = drop();
    }

    table carbon_metric_component_idle_power {
        key = {
            hdr.ethernet.srcAddr: exact;
        }
        actions = {
            get_carbon_metric_idle_power;
            drop;
            NoAction;
        }
        size = 1;
        default_action = drop();
    }

    table carbon_metric_component_embedded_carbon {
        key = {
            hdr.ethernet.srcAddr: exact;
        }
        actions = {
            get_carbon_metric_embedded_carbon;
            drop;
            NoAction;
        }
        size = 1;
        default_action = drop();
    }

    apply {
        // IOAM Carbon Metric Aggregation
        carbon_metric_component_energy_mix.apply();
        carbon_metric_component_idle_power.apply();
        carbon_metric_component_embedded_carbon.apply();

    }
}
