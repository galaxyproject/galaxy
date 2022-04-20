<template>
    <div>
        <ol class="rules">
            <rule-display-preview
                v-for="(rule, index) in rules"
                :key="index"
                :rule="rule"
                :index="index"
                :col-headers="columnData.colHeadersPerRule[index]" />
            <identifier-display-preview
                v-for="(map, index) in mapping"
                v-bind="map"
                :key="map.type"
                :index="index"
                :col-headers="colHeaders" />
        </ol>
    </div>
</template>
<script>
import RuleDefs from "mvc/rules/rule-definitions";
import RuleDisplayPreview from "./RuleDisplayPreview";
import IdentifierDisplayPreview from "./IdentifierDisplayPreview";

export default {
    components: {
        RuleDisplayPreview,
        IdentifierDisplayPreview,
    },
    props: {
        inputRules: {
            required: false,
            type: Object,
        },
    },
    data: function () {
        return {};
    },
    computed: {
        mapping: function () {
            return this.inputRules ? this.inputRules.mapping : [];
        },
        rules: function () {
            return this.inputRules ? this.inputRules.rules : [];
        },
        columnData: function () {
            const hotData = RuleDefs.applyRules([], [], [], this.rules);
            const colHeadersPerRule = hotData.colHeadersPerRule;
            return { colHeadersPerRule: colHeadersPerRule, columns: hotData.columns };
        },
        colHeaders: function () {
            const columns = this.columnData.columns;
            return RuleDefs.colHeadersFor([], columns);
        },
    },
};
</script>
