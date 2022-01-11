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
                    <h2 v-else class="text-center my-3" id="basic-disk-usage-summary">
                        You're using <b>{{ getTotalDiskUsage(user) }}</b> of disk space.
                    </h2>
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
        };
    },
    methods: {
        getTotalDiskUsage(user) {
            return bytesToString(user.total_disk_usage, true);
        },
        onError(errorMessage) {
            this.errorMessage = errorMessage;
        },
    },
};
</script>
