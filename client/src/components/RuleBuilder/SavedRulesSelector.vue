<template>
    <div class="btn-group dropdown">
        <span
            id="savedRulesButton"
            v-b-tooltip.hover.bottom
            class="fas fa-history rule-builder-view-source"
            :class="{ disabled: numOfSavedRules == 0 }"
            :title="savedRulesMenu"
            data-toggle="dropdown"></span>
        <div class="dropdown-menu" role="menu">
            <a
                v-for="(session, index) in sortSavedRules"
                :key="session.dateTime"
                v-b-tooltip.hover.right
                class="rule-link dropdown-item saved-rule-item"
                :title="formatPreview(session.rule, index)"
                @click="$emit('update-rules', session.rule)"
                >Saved rule from
                <UtcDate :date="session.dateTime" mode="elapsed" />
            </a>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import _l from "utils/localization";
import BootstrapVue from "bootstrap-vue";
import { RULES, MAPPING_TARGETS } from "mvc/rules/rule-definitions";
import UtcDate from "components/UtcDate";

Vue.use(BootstrapVue);
export default {
    components: {
        UtcDate,
    },
    props: {
        savedRules: {
            type: Array,
            required: true,
        },
        ruleColHeaders: {
            type: Array,
            required: true,
        },
    },
    data: function () {
        return {
            savedRulesMenu: _l("Recently used rules"),
        };
    },
    computed: {
        numOfSavedRules: function () {
            return this.savedRules.length;
        },
        sortSavedRules: function () {
            return [...this.savedRules].sort(this.onSessionDateTime);
        },
    },
    methods: {
        formatPreview(savedRuleJson, index) {
            let prettyString = "";
            let delim = "";
            let numOfPreviewedRules = 0;
            const savedRule = JSON.parse(savedRuleJson);
            savedRule.rules.forEach((element) => {
                if (numOfPreviewedRules == 5) {
                    return prettyString;
                } else {
                    prettyString += delim + RULES[element.type].display(element, this.ruleColHeaders[index]);
                    prettyString = prettyString.slice(0, -1);
                    delim = ", ";
                    numOfPreviewedRules++;
                }
            });
            savedRule.mapping.forEach((element) => {
                if (numOfPreviewedRules == 5) {
                    return prettyString;
                } else {
                    prettyString += delim + "Set " + MAPPING_TARGETS[element.type].label;
                    delim = ", ";
                    numOfPreviewedRules++;
                }
            });
            return prettyString;
        },
        onSessionDateTime(a, b) {
            var first = new Date(a.dateTime).getTime();
            var second = new Date(b.dateTime).getTime();
            return second - first;
        },
    },
};
</script>

<style>
.saved-rule-item:hover {
    color: white !important;
}
</style>
