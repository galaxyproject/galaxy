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
                v-for="session in sortSavedRules"
                :key="session.dateTime"
                @click="$emit('update-rules', session.rule)"
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
    },
    computed: {
        numOfSavedRules: function () {
            return this.savedRules.length;
        },
        sortSavedRules: function () {
            return this.savedRules.sort(this.onSessionDateTime);
        },
    },
    methods: {
        formatDate(dateTime) {
            return moment.utc(dateTime).from(moment().utc());
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
