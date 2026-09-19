<script setup lang="ts">
import { computed, watch } from "vue";

import { useQuotaUsageStore } from "@/stores/quotaUsageStore";

import type { AnyStorageDescription } from "./types";

import ConfigurationMarkdown from "./ConfigurationMarkdown.vue";
import ObjectStoreBadges from "./ObjectStoreBadges.vue";
import ObjectStoreRestrictionSpan from "./ObjectStoreRestrictionSpan.vue";
import QuotaUsageBar from "@/components/User/DiskUsage/Quota/QuotaUsageBar.vue";

interface Props {
    storageInfo: AnyStorageDescription;
    what: string;
}

const props = defineProps<Props>();

const quotaSourceLabel = computed(() => props.storageInfo.quota?.source);
const isPrivate = computed(() => props.storageInfo.private);
const badges = computed(() => props.storageInfo.badges);
const userDefined = computed(() => props.storageInfo.object_store_id?.startsWith("user_objects://"));

const quotaUsageStore = useQuotaUsageStore();
const quotaSourceKey = computed(() => quotaSourceLabel.value ?? "__null__");
const isLoadingUsage = computed(() => Boolean(quotaUsageStore.loadingBySource[quotaSourceKey.value]));
const quotaUsage = computed(() => quotaUsageStore.getQuotaUsageBySourceLabel(quotaSourceLabel.value) ?? null);

watch(
    () => [props.storageInfo.quota?.enabled, quotaSourceLabel.value] as const,
    ([enabled, sourceLabel]) => {
        if (!enabled) {
            return;
        }

        void quotaUsageStore.loadQuotaUsageForSource(sourceLabel, true);
    },
    { immediate: true },
);

defineExpose({
    isPrivate,
});
</script>

<script lang="ts">
export default {
    name: "DescribeObjectStore",
};
</script>

<template>
    <div>
        <div>
            <span v-localize>{{ what }}</span>
            <span v-if="storageInfo.name" class="display-os-by-name">
                a Galaxy <ObjectStoreRestrictionSpan :is-private="isPrivate" /> storage named
                <b>{{ storageInfo.name }}</b>
            </span>
            <span v-else-if="storageInfo.object_store_id" class="display-os-by-id">
                a Galaxy <ObjectStoreRestrictionSpan :is-private="isPrivate" /> storage with id
                <b>{{ storageInfo.object_store_id }}</b>
            </span>
            <span v-else class="display-os-default">
                the default configured Galaxy <ObjectStoreRestrictionSpan :is-private="isPrivate" /> storage </span
            >.
        </div>
        <ObjectStoreBadges :badges="badges"> </ObjectStoreBadges>
        <div v-if="storageInfo.quota && storageInfo.quota.enabled">
            <b-spinner v-if="isLoadingUsage" />
            <QuotaUsageBar v-else-if="quotaUsage" :quota-usage="quotaUsage" :embedded="true" />
        </div>
        <div v-else>Galaxy has no quota configured for this storage.</div>
        <ConfigurationMarkdown
            v-if="storageInfo.description"
            :markdown="storageInfo.description"
            :admin="!userDefined" />
    </div>
</template>
