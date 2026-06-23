<template>
    <div v-if="objectStore.quota.enabled">
        <LoadingSpan v-if="isLoadingUsage" :message="loadingMessage" />
        <QuotaUsageBar
            v-else-if="quotaUsage"
            :quota-usage="quotaUsage"
            :embedded="props.embedded"
            :compact="props.compact" />
    </div>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";

import type { ConcreteObjectStoreModel } from "@/api";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";

import QuotaUsageBar from "./QuotaUsageBar.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    objectStore: ConcreteObjectStoreModel;
    embedded?: boolean;
    compact?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    embedded: true,
    compact: false,
});

const loadingMessage = "Loading Galaxy storage information";

const quotaUsageStore = useQuotaUsageStore();

const quotaSourceLabel = computed(() => props.objectStore.quota.source ?? null);
const quotaSourceKey = computed(() => quotaSourceLabel.value ?? "__null__");

const quotaUsage = computed(() => quotaUsageStore.getQuotaUsageBySourceLabel(quotaSourceLabel.value) ?? null);
const isLoadingUsage = computed(
    () => quotaUsageStore.loadingAll || Boolean(quotaUsageStore.loadingBySource[quotaSourceKey.value]),
);

watch(
    () => [props.objectStore.quota.enabled, quotaSourceLabel.value] as const,
    ([enabled, sourceLabel]) => {
        if (!enabled) {
            return;
        }

        // Load all usages in a single bulk request first, then read per-source from cache.
        // This avoids N individual /api/users/current/usage/{label} requests when
        // multiple ProvidedQuotaSourceUsageBar instances mount simultaneously (e.g. in
        // a dropdown with many object store options).
        if (!quotaUsageStore.isLoaded) {
            void quotaUsageStore.loadQuotaUsages();
        } else {
            void quotaUsageStore.loadQuotaUsageForSource(sourceLabel, false);
        }
    },
    { immediate: true },
);
</script>
