<template>
    <a class="rule-link dropdown-item" href="" :class="linkClassName" @click.prevent="$emit('addNewRule', ruleType)">{{
        title
    }}</a>
</template>

<script>
import RuleDefs from "./rule-definitions";

const RULES = RuleDefs.RULES;

export default {
    props: {
        ruleType: {
            type: String,
            required: true,
        },
    },
    computed: {
        linkClassName() {
            return "rule-link-" + this.ruleType.replace(/_/g, "-");
        },
        title() {
            return RULES[this.ruleType].title;
        },
    },
};
</script>
