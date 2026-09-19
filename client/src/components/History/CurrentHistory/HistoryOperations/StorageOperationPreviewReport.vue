<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge, BListGroup, BListGroupItem } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { StorageOperationPreviewResponse } from "@/api/histories";
import { useObjectStoreStore } from "@/stores/objectStoreStore";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";
import { getIneligibleReasonDescription } from "@/utils/storageOperations";
import { bytesToString } from "@/utils/utils";

import StorageQuotaImpactBar from "@/components/History/StorageOperations/StorageQuotaImpactBar.vue";
import Popper from "@/components/Popper/Popper.vue";

const props = defineProps<{
    preview: StorageOperationPreviewResponse;
    targetStoreId: string;
}>();

interface QuotaUsageDeltaEntry {
    storeId: string;
    usageDeltaBytes: number;
}

interface QuotaImpactEntry extends QuotaUsageDeltaEntry {
    isTargetStore: boolean;
    quotaLimitBytes: number | null;
    currentUsageBytes: number;
}

const objectStoreStore = useObjectStoreStore();
const quotaUsageStore = useQuotaUsageStore();
const objectStoreUsageById = ref<Record<string, number>>({});
const objectStoreUsageLoaded = ref(false);
const objectStoreUsageLoading = ref(false);

const transferEstimate = computed(() => {
    const bytes = props.preview.estimates?.bytes_to_transfer;
    if (bytes == null) {
        return "Not available";
    }
    return bytesToString(bytes);
});

const quotaUsageDeltaEntries = computed<QuotaUsageDeltaEntry[]>(() => {
    const transfers = props.preview.estimates?.quota_delta_transfers ?? [];
    const byStore = new Map<string, number>();

    for (const transfer of transfers) {
        const bytes = transfer.bytes ?? 0;
        // Usage decreases on the source and increases on the target.
        byStore.set(transfer.source_object_store_id, (byStore.get(transfer.source_object_store_id) ?? 0) - bytes);
        byStore.set(transfer.target_object_store_id, (byStore.get(transfer.target_object_store_id) ?? 0) + bytes);
    }

    return Array.from(byStore.entries())
        .map(([storeId, usageDeltaBytes]) => ({
            storeId,
            usageDeltaBytes,
        }))
        .filter((entry) => entry.usageDeltaBytes !== 0)
        .sort((a, b) => a.storeId.localeCompare(b.storeId));
});

const affectedStoreIdsKey = computed(() => quotaUsageDeltaEntries.value.map((entry) => entry.storeId).join("|"));

function clearObjectStoreUsage(): void {
    objectStoreUsageById.value = {};
    objectStoreUsageLoaded.value = false;
}

async function ensureQuotaUsageLoadedOnce(): Promise<void> {
    if (!quotaUsageStore.isLoaded) {
        await quotaUsageStore.loadQuotaUsages();
    }
}

async function fetchObjectStoreUsageMap(): Promise<Record<string, number> | null> {
    const { data, error } = await GalaxyApi().GET("/api/users/{user_id}/objectstore_usage", {
        params: { path: { user_id: "current" } },
    });

    if (error || !data) {
        return null;
    }

    return Object.fromEntries(data.map((entry) => [entry.object_store_id, entry.total_disk_usage]));
}

async function loadObjectStoreUsageIfNeeded(): Promise<void> {
    if (!affectedStoreIdsKey.value) {
        clearObjectStoreUsage();
        return;
    }

    if (objectStoreUsageLoaded.value || objectStoreUsageLoading.value) {
        return;
    }

    objectStoreUsageLoading.value = true;
    try {
        const usageMap = await fetchObjectStoreUsageMap();
        if (!usageMap) {
            clearObjectStoreUsage();
            return;
        }

        objectStoreUsageById.value = usageMap;
        objectStoreUsageLoaded.value = true;
    } finally {
        objectStoreUsageLoading.value = false;
    }
}

function handleAffectedStoresChanged(storeIdsKey: string): void {
    if (!storeIdsKey) {
        clearObjectStoreUsage();
        return;
    }

    void loadObjectStoreUsageIfNeeded();
}

onMounted(() => {
    void ensureQuotaUsageLoadedOnce();
});

watch(affectedStoreIdsKey, handleAffectedStoresChanged, { immediate: true });

const quotaSourceByStoreId = computed<Record<string, string | null>>(() => {
    const stores = objectStoreStore.selectableObjectStores ?? [];
    return Object.fromEntries(
        stores
            .filter((store) => Boolean(store.object_store_id))
            .map((store) => [store.object_store_id!, store.quota.source ?? null]),
    );
});

const maxUsageScaleBytes = computed(() => {
    const scaleCandidates = quotaImpactEntries.value.flatMap((entry) => {
        const currentUsage = entry.currentUsageBytes;
        const projectedUsage = Math.max(0, currentUsage + entry.usageDeltaBytes);
        return [currentUsage, projectedUsage];
    });

    if (!scaleCandidates.length) {
        return 1;
    }

    return Math.max(1, ...scaleCandidates);
});

const quotaProjection = computed<QuotaProjection | null>(() => props.preview.estimates.quota_projection ?? null);

const quotaImpactEntries = computed<QuotaImpactEntry[]>(() => {
    return quotaUsageDeltaEntries.value.map((entry) => {
        const isTargetStore = entry.storeId === props.targetStoreId;
        const quotaSourceLabel = quotaSourceByStoreId.value[entry.storeId] ?? null;
        const quotaUsage = quotaUsageStore.getQuotaUsageBySourceLabel(quotaSourceLabel) ?? null;
        return {
            ...entry,
            isTargetStore,
            quotaLimitBytes: quotaUsage?.quotaInBytes ?? null,
            currentUsageBytes:
                objectStoreUsageById.value[entry.storeId] ??
                (isTargetStore && quotaProjection.value
                    ? quotaProjection.value.projected_usage + entry.usageDeltaBytes
                    : 0),
        };
    });
});

const ineligibleReasonBreakdown = computed(() => {
    return (props.preview.eligibility?.reasons ?? [])
        .map((reason) => ({
            code: reason.reason_code,
            count: reason.count,
        }))
        .sort((a, b) => b.count - a.count);
});

const hasIneligible = computed(() => props.preview.eligibility.ineligible_count > 0);
const noneEligible = computed(() => props.preview.eligibility.eligible_count === 0);
const hasWarnings = computed(() => Boolean(props.preview.warnings?.length) || noneEligible.value);

type QuotaProjection = NonNullable<StorageOperationPreviewResponse["estimates"]["quota_projection"]>;

const targetStoreName = computed(() => {
    return objectStoreStore.getObjectStoreNameById(props.targetStoreId) ?? "Unknown storage location";
});

function getObjectStoreLabel(storeId: string) {
    return objectStoreStore.getObjectStoreNameById(storeId) ?? "Unknown storage location";
}
</script>

<template>
    <div class="storage-operation-preview-report">
        <!-- Destination -->
        <p class="mb-3">
            <span class="text-muted">Moving to: </span>
            <strong>{{ targetStoreName }}</strong>
        </p>

        <!-- Selection counts -->
        <div class="d-flex flex-wrap mb-3">
            <div class="mr-4 mb-2">
                <div class="font-weight-bold h5 mb-0">{{ preview.selection_counts.selected_items_count }}</div>
                <small class="text-muted">Selected items</small>
            </div>
            <div class="mr-4 mb-2">
                <div class="font-weight-bold h5 mb-0">{{ preview.selection_counts.expanded_leaf_count }}</div>
                <small class="text-muted">Expanded datasets</small>
            </div>
            <div class="mr-4 mb-2">
                <div class="font-weight-bold h5 mb-0">{{ preview.selection_counts.unique_dataset_count }}</div>
                <small class="text-muted">Unique datasets</small>
            </div>
        </div>

        <!-- Eligibility summary -->
        <div class="d-flex align-items-center flex-wrap mb-3">
            <BBadge variant="success" class="mr-2 mb-1 px-2 py-1">
                {{ preview.eligibility.eligible_count }} eligible
            </BBadge>
            <BBadge :variant="hasIneligible ? 'danger' : 'secondary'" class="mr-3 mb-1 px-2 py-1">
                {{ preview.eligibility.ineligible_count }} ineligible
            </BBadge>
            <span class="text-muted small mb-1">Estimated transfer: {{ transferEstimate }}</span>
        </div>

        <!-- Storage quota changes -->
        <div v-if="quotaUsageDeltaEntries.length" class="mb-3">
            <div class="d-flex align-items-center mb-2">
                <p class="mb-0 font-weight-bold">Quota availability impact by location:</p>
                <Popper placement="top" mode="light">
                    <template v-slot:reference>
                        <span class="ml-2 text-muted" aria-label="Quota impact help" tabindex="0">
                            <FontAwesomeIcon :icon="faInfoCircle" />
                        </span>
                    </template>
                    <div class="p-2 small" style="max-width: 28rem">
                        Based on current usage and quota limits, the bars below illustrate how available quota will
                        change on each affected storage location if the operation is executed. The "Current" and "After
                        Change" values represent total usage on that storage location before and after the operation,
                        while "Gain" or "Loss" reflects the usage change for that location. These are estimates based on
                        current information and actual results may vary at execution time.
                    </div>
                </Popper>
            </div>
            <p class="mb-2 text-muted small">You can hover over each bar for more details.</p>
            <StorageQuotaImpactBar
                v-for="entry in quotaImpactEntries"
                :key="entry.storeId"
                :store-label="getObjectStoreLabel(entry.storeId)"
                :current-usage-bytes="entry.currentUsageBytes"
                :delta-bytes="entry.usageDeltaBytes"
                :quota-limit-bytes="entry.quotaLimitBytes"
                :scale-max-bytes="maxUsageScaleBytes"
                :is-target-store="entry.isTargetStore" />
            <div v-if="!quotaImpactEntries.length" class="text-muted small">
                No quota availability changes were detected for this operation.
            </div>
        </div>

        <!-- Ineligibility breakdown -->
        <div v-if="ineligibleReasonBreakdown.length" class="mb-3">
            <p class="mb-1 font-weight-bold">Why some datasets cannot be moved:</p>
            <BListGroup flush>
                <BListGroupItem
                    v-for="reason in ineligibleReasonBreakdown"
                    :key="reason.code"
                    class="px-0 py-2 d-flex align-items-start border-0">
                    <BBadge variant="danger" class="mr-2 mt-1 flex-shrink-0">{{ reason.count }}</BBadge>
                    <div>
                        <div class="font-weight-bold small">
                            {{ getIneligibleReasonDescription(reason.code).label }}
                        </div>
                        <div v-if="getIneligibleReasonDescription(reason.code).description" class="text-muted small">
                            {{ getIneligibleReasonDescription(reason.code).description }}
                        </div>
                    </div>
                </BListGroupItem>
            </BListGroup>
        </div>

        <!-- Warnings -->
        <BAlert v-if="hasWarnings" show variant="warning" class="mb-0 py-2">
            <div class="font-weight-bold small mb-1">Warnings</div>
            <div v-for="(warning, index) in preview.warnings" :key="index" class="small py-1">
                {{ warning }}
            </div>
            <div v-if="noneEligible" class="small py-1">
                All selected datasets are ineligible for transfer. Please review the reasons above and adjust your
                selection or target storage location.
            </div>
        </BAlert>
    </div>
</template>
