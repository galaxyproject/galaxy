<template>
    <li class="rule">
        <span v-b-tooltip.hover :title="help">Set {{ columnsLabel }} as {{ typeDisplay }}</span>
        <FontAwesomeIcon v-b-tooltip.hover :title="titleEdit" icon="fa-edit" @click="edit" />
        <FontAwesomeIcon v-b-tooltip.hover :title="titleRemove" icon="fa-times" @click="remove" />
    </li>
</template>

<script>
import _l from "utils/localization";
import RuleDefs from "./rule-definitions";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes, faEdit } from "@fortawesome/free-solid-svg-icons";

library.add(faTimes, faEdit);

const MAPPING_TARGETS = RuleDefs.MAPPING_TARGETS;

export default {
    components: { FontAwesomeIcon },
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
