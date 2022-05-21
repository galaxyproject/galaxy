<template>
    <li class="rule" :title="help">Set {{ columnsLabel }} as {{ typeDisplay }}</li>
</template>

<script>
import RuleDefs from "mvc/rules/rule-definitions";

export default {
    props: {
        type: {
            type: String,
            required: true,
        },
        columns: {
            required: true,
        },
        colHeaders: {
            type: Array,
            required: true,
        },
    },
    computed: {
        typeDisplay() {
            return RuleDefs.MAPPING_TARGETS[this.type].label;
        },
        help() {
            return RuleDefs.MAPPING_TARGETS[this.type].help || "";
        },
        columnsLabel() {
            return RuleDefs.columnDisplay(this.columns, this.colHeaders);
        },
    },
};
</script>
