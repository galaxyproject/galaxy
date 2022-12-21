<template>
    <li class="rule">
        <span v-b-tooltip.hover :title="help">Set {{ columnsLabel }} as {{ typeDisplay }}</span>
        <span v-b-tooltip.hover :title="titleEdit" class="fa fa-edit" @click="edit"></span>
        <span v-b-tooltip.hover :title="titleRemove" class="fa fa-times" @click="remove"></span>
    </li>
</template>

<script>
import _l from "utils/localization";
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
