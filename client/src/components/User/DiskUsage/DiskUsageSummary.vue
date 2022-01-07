<template>
    <ConfigProvider v-slot="{ config }">
        <CurrentUser v-slot="{ user }">
            <div>
                <b-alert v-if="errorMessage" variant="danger" show>
                    <h4 class="alert-heading">Failed to access disk usage details.</h4>
                    {{ errorMessage }}
                </b-alert>
                <div v-if="user">
                    <QuotaUsageSummary v-if="config.enable_quotas" :user="user" />
                    <h2 v-else class="text-center my-3">
                        You're using <b>{{ getTotalDiskUsage(user) }}</b> of disk space.
                    </h2>
                </div>
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

export default {
    components: {
        CurrentUser,
        ConfigProvider,
        QuotaUsageSummary,
    },
    data() {
        return {
            errorMessage: null,
            loadingMessage: _l("Loading disk usage summary..."),
            noImmediatePurgeAllowedMessage: _l(
                "If you had free up some space recently, please note that your disk usage may take a while to be updated"
            ),
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
