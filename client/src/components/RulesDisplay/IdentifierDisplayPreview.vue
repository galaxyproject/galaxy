<template>
    <li class="rule" :title="help">将 {{ columnsLabel }} 设置为 {{ typeDisplay }}</li>
</template>

<script>
import RuleDefs from "components/RuleBuilder/rule-definitions";

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
