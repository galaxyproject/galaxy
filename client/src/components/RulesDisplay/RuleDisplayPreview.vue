<template>
    <li class="rule">
        <span class="rule-display">{{ title }} </span>
        <span class="rule-warning" v-if="rule.warn">
            {{ rule.warn }}
        </span>
        <span class="rule-error" v-if="rule.error">
            <span class="alert-message">{{ rule.error }}</span>
        </span>
    </li>
</template>

<script>
import RuleDefs from "mvc/rules/rule-definitions";
export default {
    props: {
        rule: {
            required: true,
            type: Object,
        },
        colHeaders: {
            type: Array,
            required: false,
        },
    },
    computed: {
        title() {
            const ruleType = this.rule.type;
            return RuleDefs.RULES[ruleType].display(this.rule, this.colHeaders);
        },
    },
    methods: {},
};
</script>
