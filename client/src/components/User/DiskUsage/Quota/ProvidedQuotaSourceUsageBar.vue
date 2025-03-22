<template>
    <QuotaSourceUsageProvider
        v-if="objectStore.quota.enabled"
        v-slot="{ result: quotaUsage, loading: isLoadingUsage }"
        :quota-source-label="objectStore.quota.source">
        <LoadingSpan v-if="isLoadingUsage" :message="loadingMessage | localize" />
        <QuotaUsageBar v-else-if="quotaUsage" :quota-usage="quotaUsage" :embedded="true" :compact="true" />
    </QuotaSourceUsageProvider>
</template>

<script>
import LoadingSpan from "components/LoadingSpan";

import QuotaUsageBar from "./QuotaUsageBar";
import { QuotaSourceUsageProvider } from "./QuotaUsageProvider";

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
            loadingMessage: "正在加载存储位置信息",
        };
    },
};
</script>
