<template>
    <b-modal visible ok-only ok-title="Close" hide-header>
        <b-alert v-if="errorMessage" variant="danger" show v-html="errorMessage" />
        <div v-else-if="usage == null">
            <span class="fa fa-spinner fa-spin" />
            <span>Please wait...</span>
        </div>
        <div class="d-block" style="overflow: hidden;" v-else>
            <div v-for="item in effectiveQuotaSourceLabels" :key="item.id">
                <quota-usage :quotaUsage="item" />
            </div>
        </div>
    </b-modal>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import { errorMessageAsString } from "utils/simple-error";
import QuotaUsage from "./QuotaUsage";

Vue.use(BootstrapVue);

export default {
    components: {
        QuotaUsage,
    },
    props: {
        quotaSourceLabels: {
            type: Array,
        },
    },
    data() {
        return {
            usage: null,
            errorMessage: null,
        };
    },
    created() {
        const url = `${getAppRoot()}api/users/current/usage`;
        axios
            .get(url)
            .then((response) => {
                this.usage = response.data;
            })
            .catch((error) => {
                this.errorMessage = errorMessageAsString(error);
            });
    },
    computed: {
        effectiveQuotaSourceLabels() {
            const labels = [];
            const usageAsDict = this.usageAsDict;
            labels.push({ id: "_default_", name: "Default Quota", ...usageAsDict["_default_"] });
            for (const label of this.quotaSourceLabels) {
                const usage = usageAsDict[label];
                labels.push({ id: label, name: `Quota Source: ${label}`, ...usage });
            }
            return labels;
        },
        usageAsDict() {
            const asDict = {};
            for (const usage of this.usage) {
                if (usage.quota_source_label == null) {
                    asDict["_default_"] = usage;
                } else {
                    asDict[usage.quota_source_label] = usage;
                }
            }
            return asDict;
        },
    },
};
</script>
