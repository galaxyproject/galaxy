<script setup lang="ts">
import ObjectStoreRestrictionSpan from "./ObjectStoreRestrictionSpan.vue";
import QuotaUsageBar from "@/components/User/DiskUsage/Quota/QuotaUsageBar.vue";
import { QuotaSourceUsageProvider } from "@/components/User/DiskUsage/Quota/QuotaUsageProvider.js";
import ObjectStoreBadges from "./ObjectStoreBadges.vue";
import ConfigurationMarkdown from "./ConfigurationMarkdown.vue";
import type { ConcreteObjectStoreModel } from "./types";

import { computed } from "vue";

interface Props {
    storageInfo: ConcreteObjectStoreModel;
    what: string;
}

const props = defineProps<Props>();

const quotaSourceLabel = computed(() => props.storageInfo.quota?.source);
const isPrivate = computed(() => props.storageInfo.private);
const badges = computed(() => props.storageInfo.badges);

defineExpose({
    isPrivate,
});
</script>

<template>
    <div>
        <div>
            <span v-localize>{{ what }}</span>
            <span v-if="storageInfo.name" class="display-os-by-name">
                a Galaxy <object-store-restriction-span :is-private="isPrivate" /> object store named
                <b>{{ storageInfo.name }}</b>
            </span>
            <span v-else-if="storageInfo.object_store_id" class="display-os-by-id">
                a Galaxy <object-store-restriction-span :is-private="isPrivate" /> object store with id
                <b>{{ storageInfo.object_store_id }}</b>
            </span>
            <span v-else class="display-os-default">
                the default configured Galaxy <object-store-restriction-span :is-private="isPrivate" /> object store </span
            >.
        </div>
        <ObjectStoreBadges :badges="badges"> </ObjectStoreBadges>
        <QuotaSourceUsageProvider
            v-if="storageInfo.quota && storageInfo.quota.enabled"
            v-slot="{ result: quotaUsage, loading: isLoadingUsage }"
            :quota-source-label="quotaSourceLabel">
            <b-spinner v-if="isLoadingUsage" />
            <QuotaUsageBar v-else-if="quotaUsage" :quota-usage="quotaUsage" :embedded="true" />
        </QuotaSourceUsageProvider>
        <div v-else>Galaxy has no quota configured for this object store.</div>
        <ConfigurationMarkdown v-if="storageInfo.description" :markdown="storageInfo.description" :admin="true" />
    </div>
</template>
