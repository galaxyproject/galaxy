<template>
    <div class="btn-group dropdown">
        <span
            class="fas fa-history rule-builder-view-source"
            v-bind:class="{ disabled: numOfSavedRules == 0 }"
            v-b-tooltip.hover.bottom
            :title="savedRulesMenu"
            data-toggle="dropdown"
            id="savedRulesButton"
        ></span>
        <div class="dropdown-menu" role="menu">
            <a
                class="rule-link dropdown-item saved-rule-item"
                v-for="session in getRules()"
                :key="session.dateTime"
                v-on:click="$emit('update-rules', JSON.parse(session.rule))"
            >{{ session.dateTime }}</a>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import _l from "utils/localization";
import BootstrapVue from "bootstrap-vue";
Vue.use(BootstrapVue);
export default {
    data: function () {
        return {
            savedRulesMenu: _l("Recently used rules"),
        };
    },
    props: {
        builder: {
            required: true,
        },
    },
    computed: {
        numOfSavedRules: function () {
            return this.getRules().length;
        },
    },
    methods: {
        getRules() {
            var savedRules = [];
            var counter = 0;
            var regExpForSavedRules = /Saved Rule:.*/;
            for (var i = 0; i < localStorage.length; i++) {
                if (regExpForSavedRules.test(localStorage.key(i))) {
                    savedRules.push({
                        dateTime: localStorage.key(i), 
                        rule: localStorage.getItem(localStorage.key(i))
                    });
                    counter++;
                    if (counter == 10) {
                        break;
                    }
                }
            }
            return savedRules;
        },
        saveSession(jsonRules) {
            var dateTimeString = "Saved Rule: " + new Date().toISOString();
            localStorage.setItem(dateTimeString, jsonRules);
        },
    },
};
</script>

<style>
.saved-rule-item:hover {
    color: white !important;
}
</style>
