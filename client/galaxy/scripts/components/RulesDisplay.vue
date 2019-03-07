<template>
    <div>
        <ol class="rules">
            <rule-display-preview
                v-for="(rule, index) in rules"
                v-bind:rule="rule"
                v-bind:index="index"
                v-bind:key="index"
                :col-headers="columnData.colHeadersPerRule[index]"
            />
            <identifier-display-preview
                v-for="(map, index) in mapping"
                v-bind="map"
                v-bind:index="index"
                v-bind:key="map.type"
                :col-headers="colHeaders"
            />
        </ol>
    </div>
</template>
<script>
import RuleDefs from "mvc/rules/rule-definitions";

// read-only variants of the components for displaying these rules and mappings in builder widget.
const RuleDisplayPreview = {
    template: `
        <li class="rule">
            <span class="rule-display">{{ title }}
            </span>
            <span class="rule-warning" v-if="rule.warn">
                {{ rule.warn }}
            </span>
            <span class="rule-error" v-if="rule.error">
                <span class="alert-message">{{ rule.error }}</span>
            </span>
        </li>
    `,
    props: {
        rule: {
            required: true,
            type: Object
        },
        colHeaders: {
            type: Array,
            required: false
        }
    },
    computed: {
        title() {
            const ruleType = this.rule.type;
            return RuleDefs.RULES[ruleType].display(this.rule, this.colHeaders);
        }
    },
    methods: {}
};

const IdentifierDisplayPreview = {
    template: `
      <li class="rule" :title="help">
        Set {{ columnsLabel }} as {{ typeDisplay }}
      </li>
    `,
    props: {
        type: {
            type: String,
            required: true
        },
        columns: {
            required: true
        },
        colHeaders: {
            type: Array,
            required: true
        }
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
        }
    }
};

export default {
    data: function() {
        return {};
    },
    computed: {
        mapping: function() {
            return this.inputRules ? this.inputRules.mapping : [];
        },
        rules: function() {
            return this.inputRules ? this.inputRules.rules : [];
        },
        columnData: function() {
            const colHeadersPerRule = [];
            const hotData = RuleDefs.applyRules([], [], [], this.rules, colHeadersPerRule);
            return { colHeadersPerRule: colHeadersPerRule, columns: hotData.columns };
        },
        colHeaders: function() {
            const columns = this.columnData.columns;
            return RuleDefs.colHeadersFor([], columns);
        }
    },
    props: {
        inputRules: {
            required: false,
            type: Object
        }
    },
    components: {
        RuleDisplayPreview,
        IdentifierDisplayPreview
    }
};
</script>
