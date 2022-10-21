<template>
    <ConfigProvider v-slot="{ config }">
        <CurrentUser v-slot="{ user }">
            <div>
                <b-alert v-if="errorMessage" variant="danger" show>
                    <h2 class="alert-heading h-sm">{{ errorMessageTitle }}</h2>
                    {{ errorMessage }}
                </b-alert>
                <b-container v-if="user">
                    <b-row v-if="config.enable_quotas" class="justify-content-md-center">
                        <QuotaUsageSummary v-if="quotaUsages" :quota-usages="quotaUsages" />
                    </b-row>
                    <h2 v-else id="basic-disk-usage-summary" class="text-center my-3">
                        You're using <b>{{ getTotalDiskUsage(user) }}</b> of disk space.
                    </h2>
                </b-container>
                <b-container class="text-center mb-5 w-75">
                    <button
                        title="Recalculate disk usage"
                        :disabled="isRecalculating"
                        variant="outline-secondary"
                        size="sm"
                        pill
                        @click="onRefresh">
                        <b-spinner v-if="isRecalculating" small />
                        <span v-else>Refresh</span>
                    </button>
                    <b-alert
                        v-if="isRecalculating"
                        class="mt-2"
                        variant="info"
                        dismissible
                        fade
                        :show="dismissCountDown"
                        @dismiss-count-down="countDownChanged">
                        Recalculating disk usage... this may take some time, please check back later.
                    </b-alert>
                </b-container>
            </div>
        </CurrentUser>
    </ConfigProvider>
</template>

<script>
import _l from "utils/localization";
import { bytesToString } from "utils/utils";
import CurrentUser from "components/providers/CurrentUser";
import ConfigProvider from "components/providers/ConfigProvider";
import QuotaUsageSummary from "components/User/DiskUsage/Quota/QuotaUsageSummary";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { QuotaUsage } from "./Quota/model";
import { mapGetters } from "vuex";

export default {
    components: {
        CurrentUser,
        ConfigProvider,
        QuotaUsageSummary,
    },
    data() {
        return {
            errorMessageTitle: _l("Failed to access disk usage details."),
            errorMessage: null,
            isRecalculating: false,
            dismissCountDown: 0,
        };
    },
    computed: {
        ...mapGetters("user", ["currentUser"]),
        quotaUsages() {
            return [new QuotaUsage(this.currentUser)];
        },
    },
    methods: {
        getTotalDiskUsage(user) {
            return bytesToString(user.total_disk_usage, true);
        },
        onError(errorMessage) {
            this.errorMessage = errorMessage;
        },
        async onRefresh() {
            await this.requestDiskUsageRecalculation();
            await this.displayRecalculationForSeconds(30);

            this.$store.dispatch("user/loadUser");
        },
        async requestDiskUsageRecalculation() {
            try {
                await axios.put(`${getAppRoot()}api/users/recalculate_disk_usage`);
            } catch (e) {
                rethrowSimple(e);
            }
        },
        async displayRecalculationForSeconds(seconds) {
            return new Promise((resolve) => {
                this.isRecalculating = true;
                this.dismissCountDown = seconds;

                setTimeout(() => {
                    this.isRecalculating = false;
                    resolve();
                }, seconds * 1000);
            });
        },
        countDownChanged(dismissCountDown) {
            this.dismissCountDown = dismissCountDown;
        },
    },
};
</script>
