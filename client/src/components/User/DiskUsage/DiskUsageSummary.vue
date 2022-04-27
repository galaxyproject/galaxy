<template>
    <ConfigProvider v-slot="{ config }">
        <CurrentUser v-slot="{ user }">
            <div>
                <b-alert v-if="errorMessage" variant="danger" show>
                    <h4 class="alert-heading">{{ errorMessageTitle }}</h4>
                    {{ errorMessage }}
                </b-alert>
                <b-container v-if="user">
                    <b-row v-if="config.enable_quotas" class="justify-content-md-center">
                        <QuotaUsageProvider v-slot="{ result: quotaUsages, loading: isLoadingUsage }">
                            <b-spinner v-if="isLoadingUsage" />
                            <QuotaUsageSummary v-else-if="quotaUsages" :quota-usages="quotaUsages" />
                        </QuotaUsageProvider>
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
import { QuotaUsageProvider } from "./Quota/QuotaUsageProvider";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { rethrowSimple } from "utils/simple-error";

export default {
    components: {
        CurrentUser,
        ConfigProvider,
        QuotaUsageSummary,
        QuotaUsageProvider,
    },
    data() {
        return {
            errorMessageTitle: _l("Failed to access disk usage details."),
            errorMessage: null,
            isRecalculating: false,
            dismissCountDown: 0,
        };
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
            this.displayRecalculationForSeconds(30);
        },
        async requestDiskUsageRecalculation() {
            try {
                await axios.put(`${getAppRoot()}api/users/recalculate_disk_usage`);
            } catch (e) {
                rethrowSimple(e);
            }
        },
        displayRecalculationForSeconds(seconds) {
            this.isRecalculating = true;
            this.dismissCountDown = seconds;
            setTimeout(() => {
                this.isRecalculating = false;
            }, seconds * 1000);
        },
        countDownChanged(dismissCountDown) {
            this.dismissCountDown = dismissCountDown;
        },
    },
};
</script>
