<script setup lang="ts">
import { BAlert, BBadge, BPagination } from "bootstrap-vue";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import {
    getStorageOperationRunItemsWithTotal,
    type HistoryReference,
    type StorageOperationRunItemStatus,
} from "@/api/histories";
import type { TableField } from "@/components/Common/GTable.types";
import { useStorageRunWatcher } from "@/composables/useStorageRunWatcher";
import { useObjectStoreStore } from "@/stores/objectStoreStore";
import { useStorageOperationsStore } from "@/stores/storageOperationsStore";
import Filtering, { contains } from "@/utils/filtering";
import localize from "@/utils/localization";
import { getIneligibleReasonDescription, toTrackedStorageRun } from "@/utils/storageOperations";
import { bytesToString } from "@/utils/utils";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import DatasetPopoverLink from "@/components/Common/DatasetPopoverLink.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import GTable from "@/components/Common/GTable.vue";
import Heading from "@/components/Common/Heading.vue";
import StorageOperationOutcomeProgress from "@/components/History/StorageOperations/StorageOperationOutcomeProgress.vue";
import StorageOperationRunStateBadge from "@/components/History/StorageOperations/StorageOperationRunStateBadge.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    historyId: string;
    runId: string;
}>();

const history: HistoryReference = {
    id: props.historyId,
    model_class: "History",
};

const { runStatus, isTerminal, startPolling, stopPolling } = useStorageRunWatcher(history, props.runId);
const storageOperationsStore = useStorageOperationsStore();
const objectStoreStore = useObjectStoreStore();

const run = computed(() => runStatus.value?.run);
const pageItems = ref<StorageOperationRunItemStatus[]>([]);
const isLoadingItems = ref(false);
const itemsTotalMatches = ref(0);
const filterText = ref("");
const showAdvanced = ref(false);
const currentPage = ref(1);
const perPage = 50;

const runItemFilterClass = new Filtering(
    {
        dataset_id: {
            placeholder: "dataset id",
            type: String,
            handler: contains("dataset_id"),
            menuItem: true,
        },
        reason_code: {
            placeholder: "reason code",
            type: String,
            handler: contains("reason_code"),
            menuItem: true,
        },
    },
    undefined,
    true,
    false,
);

const breadcrumbItems = computed(() => [
    { title: "History Storage Operations", to: `/histories/${props.historyId}/storage/runs` },
    { title: "Storage Operation Run" },
]);

const tableFields: TableField[] = [
    { key: "dataset_id", label: localize("Dataset"), width: "260px" },
    { key: "state", label: localize("State"), width: "120px" },
    { key: "reason_code", label: localize("Reason code"), width: "180px" },
    { key: "reason_text", label: localize("Reason"), sortable: false, class: "run-item-reason" },
];

const failedOrSkippedCount = computed(() => (run.value?.failed_count ?? 0) + (run.value?.skipped_count ?? 0));
const displayItems = computed(() => pageItems.value);
const totalDataCopiedDisplay = computed(() => {
    const totalBytesProcessed = run.value?.total_bytes_processed ?? 0;
    const succeededCount = run.value?.succeeded_count ?? 0;
    if (totalBytesProcessed === 0 && succeededCount > 0) {
        return localize("No data transfer required");
    }
    return bytesToString(totalBytesProcessed);
});

const failedItemsEmptyStateMessage = computed(() => {
    if (!isTerminal.value) {
        return localize("No failed or skipped items yet. This run is still in progress.");
    }
    return localize("No failed or skipped items for this run.");
});

const maxPage = computed(() => {
    return Math.max(1, Math.ceil(itemsTotalMatches.value / perPage));
});

const targetStoreDisplayName = computed(() => {
    return (
        objectStoreStore.getObjectStoreNameById(run.value?.target_object_store_id) ??
        run.value?.target_object_store_id ??
        ""
    );
});

function onPageChange(page: number) {
    currentPage.value = page;
}

function buildItemsSearchQuery(filterText: string) {
    const filter = filterText.trim();
    return filter ? `state:failed state:skipped ${filter}` : "state:failed state:skipped";
}

async function loadFailedOrSkippedPage() {
    if (!run.value || failedOrSkippedCount.value === 0) {
        pageItems.value = [];
        itemsTotalMatches.value = 0;
        return;
    }

    isLoadingItems.value = true;
    try {
        const offset = (currentPage.value - 1) * perPage;
        const search = buildItemsSearchQuery(filterText.value);
        const result = await getStorageOperationRunItemsWithTotal(history, props.runId, {
            offset,
            limit: perPage,
            search,
        });
        pageItems.value = result.data;
        itemsTotalMatches.value = result.totalMatches ?? failedOrSkippedCount.value;
    } finally {
        isLoadingItems.value = false;
    }
}

function getItemStateVariant(state: string) {
    if (state === "failed") {
        return "danger";
    }
    if (state === "skipped") {
        return "warning";
    }
    return "secondary";
}

function getReasonText(reasonCode: string | null | undefined) {
    if (!reasonCode) {
        return "-";
    }
    return localize(getIneligibleReasonDescription(reasonCode).description);
}

watch(filterText, () => {
    currentPage.value = 1;
    void loadFailedOrSkippedPage();
});

watch(maxPage, () => {
    if (currentPage.value > maxPage.value) {
        currentPage.value = maxPage.value;
    }
});

watch(
    [currentPage, failedOrSkippedCount],
    () => {
        void loadFailedOrSkippedPage();
    },
    { immediate: true },
);

watch(
    run,
    (currentRun) => {
        if (!currentRun) {
            return;
        }

        storageOperationsStore.startRun(toTrackedStorageRun(props.historyId, currentRun));
    },
    { immediate: true },
);

onMounted(() => {
    startPolling();
});

onBeforeUnmount(() => {
    stopPolling();
});
</script>

<template>
    <div class="storage-operation-run-view p-3">
        <BreadcrumbHeading :items="breadcrumbItems" />

        <LoadingSpan v-if="!run" :message="localize('Loading storage operation run status')" />

        <template v-else>
            <BAlert show variant="secondary">
                <div class="d-flex align-items-center flex-wrap">
                    <strong class="mr-2">{{ localize("State:") }}</strong>
                    <StorageOperationRunStateBadge
                        class="mr-3"
                        :state="run.state"
                        :failed-count="run.failed_count"
                        :skipped-count="run.skipped_count" />
                    <span class="mr-3">
                        <strong>{{ localize("Mode:") }}</strong> {{ run.mode }}
                    </span>
                    <span>
                        <strong>{{ localize("Target store:") }}</strong> {{ targetStoreDisplayName }}
                    </span>
                </div>
            </BAlert>

            <div class="mb-3">
                <strong>{{ localize("Total:") }}</strong> {{ run.total_count }}
                <span class="mx-2">|</span>
                <strong>{{ localize("Succeeded:") }}</strong> {{ run.succeeded_count }}
                <span class="mx-2">|</span>
                <strong>{{ localize("Failed:") }}</strong> {{ run.failed_count }}
                <span class="mx-2">|</span>
                <strong>{{ localize("Skipped:") }}</strong> {{ run.skipped_count }}
                <span class="mx-2">|</span>
                <strong>{{ localize("Data transferred:") }}</strong> {{ totalDataCopiedDisplay }}
            </div>

            <div class="mb-3">
                <StorageOperationOutcomeProgress
                    :total-count="run.total_count"
                    :succeeded-count="run.succeeded_count"
                    :failed-count="run.failed_count"
                    :skipped-count="run.skipped_count"
                    height-class="storage-operation-progress-md" />
            </div>

            <BAlert v-if="!isTerminal" show variant="info">
                {{ localize("This run is still in progress. Status is updated automatically.") }}
            </BAlert>

            <div class="mt-3">
                <Heading h3 size="sm">{{ localize("Failed or Skipped Items") }}</Heading>

                <FilterMenu
                    class="run-item-filter mb-2"
                    name="Storage Run Items"
                    view="compact"
                    placeholder="search failed/skipped items"
                    :filter-class="runItemFilterClass"
                    :filter-text.sync="filterText"
                    :loading="isLoadingItems"
                    :show-advanced.sync="showAdvanced" />

                <LoadingSpan v-if="isLoadingItems" class="mb-2" :message="localize('Loading failed/skipped items')" />

                <GTable
                    id="storage-operation-run-items-table"
                    striped
                    hover
                    stacked="md"
                    show-empty
                    :fields="tableFields"
                    :items="displayItems"
                    :current-page="1"
                    :per-page="0"
                    :local-sorting="false"
                    :local-filtering="false"
                    :empty-state="{ message: failedItemsEmptyStateMessage }">
                    <template v-slot:cell(dataset_id)="slot">
                        <DatasetPopoverLink :dataset-id="slot.item.dataset_id" />
                    </template>

                    <template v-slot:cell(state)="slot">
                        <BBadge :variant="getItemStateVariant(slot.item.state)">{{ slot.item.state }}</BBadge>
                    </template>

                    <template v-slot:cell(reason_code)="slot">
                        <span>{{ slot.item.reason_code || "-" }}</span>
                    </template>

                    <template v-slot:cell(reason_text)="slot">
                        <span>{{ getReasonText(slot.item.reason_code) }}</span>
                    </template>
                </GTable>

                <div v-if="itemsTotalMatches > perPage" class="d-flex justify-content-end mt-2">
                    <BPagination
                        :value="currentPage"
                        :total-rows="itemsTotalMatches"
                        :per-page="perPage"
                        align="right"
                        size="sm"
                        first-number
                        last-number
                        @change="onPageChange" />
                </div>
            </div>
        </template>
    </div>
</template>

<style scoped>
.run-item-filter {
    min-width: 280px;
    max-width: 520px;
}

:deep(.run-item-reason) {
    white-space: normal;
    word-break: break-word;
}
</style>
