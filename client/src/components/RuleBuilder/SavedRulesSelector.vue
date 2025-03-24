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
                :key="index"
                v-b-tooltip.hover.right
                class="rule-link dropdown-item saved-rule-item"
                :title="formatPreview(session.rule)"
                @click="$emit('update-rules', session.rule)"
                >保存于
                <UtcDate :date="session.dateTime" mode="elapsed" />
                的规则
            </a>
        </div>
    </div>
</template>

<script>
import BootstrapVue from "bootstrap-vue";
import UtcDate from "components/UtcDate";
import _l from "utils/localization";
import Vue from "vue";

import { MAPPING_TARGETS, RULES } from "./rule-definitions";

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
    },
    data: function () {
        return {
            savedRulesMenu: _l("最近使用的规则"),
            // Get the 61 character values for ASCII 65 (A) to 126 (~), which is how handson table labels its columns
            // This ensures the handson table headers are available for passing to the display method in formatPreview
            hotHeaders: [...new Array(61).keys()].map((i) => String.fromCharCode(i + 65)),
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
        formatPreview(savedRuleJson) {
            let prettyString = "";
            let delim = "";
            let numOfPreviewedRules = 0;
            const savedRule = JSON.parse(savedRuleJson);
            savedRule.rules.forEach((element) => {
                if (numOfPreviewedRules == 5) {
                    return prettyString;
                } else {
                    prettyString += delim + RULES[element.type].display(element, this.hotHeaders);
                    prettyString = prettyString.trim();
                    delim = ", ";
                    numOfPreviewedRules++;
                }
            });
            savedRule.mapping.forEach((element) => {
                if (numOfPreviewedRules == 5) {
                    return prettyString;
                } else {
                    prettyString += delim + "设置 " + MAPPING_TARGETS[element.type].label;
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
