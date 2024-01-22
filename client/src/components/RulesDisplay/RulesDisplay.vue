<template>
    <div>
        <ol class="rules">
            <RuleDisplayPreview
                v-for="(rule, index) in rules"
                :key="index"
                :rule="rule"
                :index="index"
                :col-headers="columnData.colHeadersPerRule[index]" />
            <IdentifierDisplayPreview
                v-for="(map, index) in mapping"
                v-bind="map"
                :key="map.type"
                :index="index"
                :col-headers="colHeaders" />
        </ol>
    </div>
</template>
<script>
import RuleDefs from "components/RuleBuilder/rule-definitions";

import IdentifierDisplayPreview from "./IdentifierDisplayPreview";
import RuleDisplayPreview from "./RuleDisplayPreview";

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
