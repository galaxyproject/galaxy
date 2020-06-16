<template>
    <div class="btn-group dropdown">
        <span
            class="fas fa-history rule-builder-view-source"
            :class="{ disabled: numOfSavedRules == 0 }"
            v-b-tooltip.hover.bottom
            :title="savedRulesMenu"
            data-toggle="dropdown"
            id="savedRulesButton"
        ></span>
        <div class="dropdown-menu" role="menu">
            <a
                class="rule-link dropdown-item saved-rule-item"
                v-for="session in savedRules"
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
import { getGalaxyInstance } from "app";

Vue.use(BootstrapVue);
export default {
    data: function () {
        return {
            savedRulesMenu: _l("Recently used rules"),
            savedRules: [],
        };
    },
    created() {
        let counter = 0;
        if (this.user == null) {
            return;
        } else {
            for (let i = 0; i < localStorage.length; i++) {
                if (localStorage.key(i).startsWith(this.prefix + this.user)) {
                    var savedSession = localStorage.getItem(localStorage.key(i));
                    if (savedSession) {
                        var key = localStorage.key(i);
                        this.savedRules.push({
                            dateTime: key.substring(this.prefix.length + this.user.length),
                            rule: savedSession,
                        });
                    }
                    counter++;
                    if (counter == 10) {
                        break;
                    }
                }
            }
        }
    },
    props: {
        prefix: {
            type: String,
            default: "galaxy_rules_",
        },
        user: {
            type: String,
            default: getGalaxyInstance() ? getGalaxyInstance().user.id : "",
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
        saveSession(jsonRulesString) {
            var dateTimeString = new Date().toISOString();
            var key = this.prefix + this.user + dateTimeString;
            localStorage.setItem(key, jsonRulesString);
            this.savedRules.push({
                dateTime: dateTimeString,
                rule: jsonRulesString,
            });
        },
    },
};
</script>

<style>
.saved-rule-item:hover {
    color: white !important;
}
</style>
