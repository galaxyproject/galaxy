<template>
    <li class="rule" @mouseover="$emit('mouseover', $event)" @mouseout="$emit('mouseout', $event)">
        <span v-g-tooltip.hover :title="help">Set {{ columnsLabel }} as {{ typeDisplay }}</span>
        <span v-g-tooltip.hover :title="titleEdit" class="fa fa-edit" @click="edit"></span>
        <span v-g-tooltip.hover :title="titleRemove" class="fa fa-times" @click="remove"></span>
    </li>
</template>

<script>
import _l from "@/utils/localization";

import RuleDefs from "./rule-definitions";

const MAPPING_TARGETS = RuleDefs.MAPPING_TARGETS;

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
    // Under @vue/compat, undeclared listeners don't reach the root element, so the
    // hover events the rule builder uses to highlight columns are re-emitted.
    emits: ["remove", "edit", "mouseover", "mouseout"],
    computed: {
        typeDisplay() {
            return MAPPING_TARGETS[this.type].label;
        },
        help() {
            return MAPPING_TARGETS[this.type].help || "";
        },
        titleEdit() {
            return _l("Edit column definition");
        },
        titleRemove() {
            return _l("Remove this column definition");
        },
        columnsLabel() {
            return RuleDefs.columnDisplay(this.columns, this.colHeaders);
        },
    },
    methods: {
        remove() {
            this.$emit("remove");
        },
        edit() {
            this.$emit("edit");
        },
    },
};
</script>
