<template>
    <div>
        <b-alert v-if="errorMessage" variant="danger" show>
            <h4 class="alert-heading">Failed to access storage details.</h4>
            {{ errorMessage }}
        </b-alert>
        <header class="main-header">
            <h1 class="text-center my-3">
                <b>{{ title }}</b>
            </h1>
            <h4 class="text-center my-3">{{ subtitle }}</h4>
        </header>
        <b-row class="justify-content-md-center mb-3">
            <UserDetailsProvider :id="userId" v-slot="{ result: user, loading: userDetailsLoading }">
                <div>
                    <LoadingSpan v-if="userDetailsLoading" :message="loadingMessage" />
                    <QuotaUsageSummary v-if="quotasEnabled && user" :user="user"> </QuotaUsageSummary>
                </div>
            </UserDetailsProvider>
        </b-row>
    </div>
</template>

<script>
import _l from "utils/localization";
import { UserDetailsProvider } from "components/User/DiskUsage/services";
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
        quotasEnabled: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        return {
            title: _l("Storage Dashboard"),
            subtitle: _l("Here you can see an overview of your disk usage status."),
            loadingMessage: _l("Loading..."),
            errorMessage: null,
        };
    },
};
</script>
