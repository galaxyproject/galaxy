<template>
    <div>
        <b>{{ quotaUsage.name }}</b>
        <progress-bar
            :note="title"
            :ok-count="quotaUsage.quota_percent"
            :total="100"
            v-if="quotaUsage.quota_percent < 99"
        />
        <progress-bar :note="title" :error-count="quotaUsage.quota_percent" :total="100" v-else />
        <p>
            <i>Using {{ quotaUsage.nice_total_disk_usage }} out of {{ quotaUsage.quota }}.</i>
        </p>
        <hr />
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import ProgressBar from "components/ProgressBar";

Vue.use(BootstrapVue);

export default {
    components: {
        ProgressBar,
    },
    props: {
        quotaUsage: {
            type: Object,
        },
    },
    computed: {
        title() {
            if (this.quotaUsage.quota_percent == null) {
                return `Unlimited`;
            } else {
                return `Using ${this.quotaUsage.quota_percent}%.`;
            }
        },
    },
};
</script>
