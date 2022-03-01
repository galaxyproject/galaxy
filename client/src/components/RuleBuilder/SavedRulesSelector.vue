<template>
    <div class="btn-group dropdown">
        <span
            class="fas fa-history rule-builder-view-source"
            :class="{ disabled: numOfSavedRules == 0 }"
            v-b-tooltip.hover.bottom
            :title="savedRulesMenu"
            data-toggle="dropdown"
            id="savedRulesButton"></span>
        <div class="dropdown-menu" role="menu">
            <a
                class="rule-link dropdown-item saved-rule-item"
                v-for="(session, index) in savedRules"
                :key="session.dateTime"
                @click="$emit('update-rules', session.rule)"
                v-b-tooltip.hover.right
                :title="formatPreview(session.rule, index)"
                >Saved rule from {{ formatDate(session.dateTime) }}
            </a>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import _l from "utils/localization";
import BootstrapVue from "bootstrap-vue";
import moment from "moment";
import { RULES, MAPPING_TARGETS } from "mvc/rules/rule-definitions";

Vue.use(BootstrapVue);
export default {
    data: function () {
        return {
            savedRulesMenu: _l("Recently used rules"),
        };
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
    computed: {
        numOfSavedRules: function () {
            return this.savedRules.length;
        },
    },
    methods: {
        formatDate(dateTime) {
            return moment.utc(dateTime).from(moment().utc());
        },
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
    },
};
</script>

<style>
.saved-rule-item:hover {
    color: white !important;
}
</style>
