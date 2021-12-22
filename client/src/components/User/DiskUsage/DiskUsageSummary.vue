<template>
    <UserDetailsProvider :id="userId" v-slot="{ result: user, loading: userDetailsLoading }" @error="onError">
        <div>
            <b-alert v-if="errorMessage" variant="danger" show>
                <h4 class="alert-heading">Failed to access disk usage details.</h4>
                {{ errorMessage }}
            </b-alert>
            <LoadingSpan v-if="userDetailsLoading" :message="loadingMessage" />
            <div v-if="user">
                <QuotaUsageSummary v-if="quotaSettings.quotasEnabled" :user="user" :quota-settings="quotaSettings" />
                <h2 v-else class="text-center my-3">
                    You're using <b>{{ getTotalDiskUsage(user) }}</b> of disk space.
                </h2>
            </div>
        </div>
    </UserDetailsProvider>
</template>

<script>
import _l from "utils/localization";
import { bytesToString } from "utils/utils";
import { UserDetailsProvider } from "./services";
import { QuotaSettings } from "./model";
import LoadingSpan from "components/LoadingSpan";
import QuotaUsageSummary from "components/User/DiskUsage/QuotaUsageSummary";

export default {
    components: {
        UserDetailsProvider,
        LoadingSpan,
        QuotaUsageSummary,
    },
    props: {
        userId: {
            type: String,
            required: true,
        },
        quotaSettings: {
            type: QuotaSettings,
            required: true,
        },
    },
    data() {
        return {
            loadingMessage: _l("Loading disk usage summary..."),
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
