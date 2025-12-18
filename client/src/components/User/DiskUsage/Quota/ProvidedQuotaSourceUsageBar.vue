<template>
    <QuotaSourceUsageProvider
        v-if="objectStore.quota.enabled"
        v-slot="{ result: quotaUsage, loading: isLoadingUsage }"
        :quota-source-label="objectStore.quota.source">
        <LoadingSpan v-if="isLoadingUsage" :message="localize(loadingMessage)" />
        <QuotaUsageBar v-else-if="quotaUsage" :quota-usage="quotaUsage" :embedded="true" :compact="true" />
    </QuotaSourceUsageProvider>
</template>

<script>
import { localize } from "@/utils/localization";

import { QuotaSourceUsageProvider } from "./QuotaUsageProvider";

import QuotaUsageBar from "./QuotaUsageBar.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

export default {
    components: {
        LoadingSpan,
        QuotaUsageBar,
        QuotaSourceUsageProvider,
    },
    props: {
        objectStore: {
            type: Object,
            required: true,
        },
        embedded: {
            type: Boolean,
            default: true,
        },
        compact: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            loadingMessage: "Loading Galaxy storage information",
        };
    },
};
</script>
