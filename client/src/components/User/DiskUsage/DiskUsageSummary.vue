<template>
    <CurrentUser v-slot="{ user }">
        <div>
            <b-alert v-if="errorMessage" variant="danger" show>
                <h4 class="alert-heading">Failed to access disk usage details.</h4>
                {{ errorMessage }}
            </b-alert>
            <b-alert v-if="!quotaSettings.canUserPurgeImmediately" show>
                {{ noImmediatePurgeAllowedMessage }}
            </b-alert>
            <div v-if="user">
                <QuotaUsageSummary v-if="quotaSettings.quotasEnabled" :user="user" :quota-settings="quotaSettings" />
                <h2 v-else class="text-center my-3">
                    You're using <b>{{ getTotalDiskUsage(user) }}</b> of disk space.
                </h2>
            </div>
        </div>
    </CurrentUser>
</template>

<script>
import _l from "utils/localization";
import { getGalaxyInstance } from "app";
import { bytesToString } from "utils/utils";
import CurrentUser from "components/providers/CurrentUser";
import { QuotaSettings } from "./model";
import QuotaUsageSummary from "components/User/DiskUsage/QuotaUsageSummary";

export default {
    components: {
        CurrentUser,
        QuotaUsageSummary,
    },
    created() {
        const Galaxy = getGalaxyInstance();
        this.quotaSettings = QuotaSettings.create(Galaxy.config);
    },
    data() {
        return {
            quotaSettings: null,
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
