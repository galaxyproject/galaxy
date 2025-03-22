<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { QuotaSourceUsageProvider } from "@/components/User/DiskUsage/Quota/QuotaUsageProvider.js";

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

const quotaUsageProvider = ref(null);

watch(props, async () => {
    if (quotaUsageProvider.value) {
        // @ts-ignore
        quotaUsageProvider.value.update({ quotaSourceLabel: quotaSourceLabel.value });
    }
});

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
        <QuotaSourceUsageProvider
            v-if="storageInfo.quota && storageInfo.quota.enabled"
            ref="quotaUsageProvider"
            v-slot="{ result: quotaUsage, loading: isLoadingUsage }"
            :quota-source-label="quotaSourceLabel">
            <b-spinner v-if="isLoadingUsage" />
            <QuotaUsageBar v-else-if="quotaUsage" :quota-usage="quotaUsage" :embedded="true" />
        </QuotaSourceUsageProvider>
        <div v-else>Galaxy has no quota configured for this storage.</div>
        <ConfigurationMarkdown
            v-if="storageInfo.description"
            :markdown="storageInfo.description"
            :admin="!userDefined" />
    </div>
</template>
