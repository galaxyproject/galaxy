<template>
    <li class="rule">
        <span class="rule-display">
            <span class="mr-1">{{ title }}</span>
            <FontAwesomeIcon v-b-tooltip.hover :title="editTitle" icon="fa-edit" class="mr-1" @click="edit" />
            <FontAwesomeIcon v-b-tooltip.hover :title="removeTitle" icon="fa-times" class="map" @click="remove" />
        </span>
        <span v-if="rule.warn" class="rule-warning">
            {{ rule.warn }}
        </span>
        <span v-if="rule.error" class="rule-error">
            <span class="alert-message">{{ rule.error }}</span>
        </span>
    </li>
</template>

<script>
import _l from "utils/localization";
import RuleDefs from "./rule-definitions";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faTimes } from "@fortawesome/free-solid-svg-icons";

library.add(faEdit, faTimes);

const RULES = RuleDefs.RULES;

export default {
    components: { FontAwesomeIcon },
    props: {
        rule: {
            required: true,
            type: Object,
        },
        colHeaders: {
            type: Array,
            required: true,
        },
    },
    computed: {
        title() {
            const ruleType = this.rule.type;
            return RULES[ruleType].display(this.rule, this.colHeaders);
        },
        editTitle() {
            return _l("Edit this rule.");
        },
        removeTitle() {
            return _l("Remove this rule.");
        },
    },
    methods: {
        edit() {
            this.$emit("edit");
        },
        remove() {
            this.$emit("remove");
        },
    },
};
</script>
