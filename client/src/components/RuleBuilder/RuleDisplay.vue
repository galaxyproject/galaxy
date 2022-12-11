<template>
    <li class="rule">
        <span class="rule-display">
            <span class="mr-1">{{ title }}</span>
            <span v-b-tooltip.hover :title="editTitle" class="fa fa-edit mr-1" @click="edit"></span>
            <span v-b-tooltip.hover :title="removeTitle" class="fa fa-times map" @click="remove"></span>
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
const RULES = RuleDefs.RULES;

export default {
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
