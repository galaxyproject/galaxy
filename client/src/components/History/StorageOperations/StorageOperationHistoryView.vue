<script setup lang="ts">
import { BAlert, BFormInput } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import { useStorageHistoryRunsWatcher } from "@/composables/useStorageRunWatcher";
import { useHistoryStore } from "@/stores/historyStore";
import { type StorageRun, useStorageOperationsStore } from "@/stores/storageOperationsStore";
import localize from "@/utils/localization";
import { isTerminalRunState } from "@/utils/storageOperations";

import StorageOperationRunsTable from "./StorageOperationRunsTable.vue";
import Heading from "@/components/Common/Heading.vue";

type EnrichedStorageRun = ReturnType<typeof enrichRunWithSummary>;

const props = defineProps<{
    historyId: string;
}>();

const historyStore = useHistoryStore();
const storageOperationsStore = useStorageOperationsStore();

const sortBy = ref("create_time");
const sortDesc = ref(true);
const filterText = ref("");
const inProgressPage = ref(1);
const finishedPage = ref(1);
const perPage = 20;

const { startPolling, stopPolling, runSummariesByRunId } = useStorageHistoryRunsWatcher(props.historyId);

const trackedRuns = computed(() => {
    return storageOperationsStore.runs.filter((run) => run.historyId === props.historyId);
});

/**
 * Enrich tracked runs with computed fields from API summaries
 */
function enrichRunWithSummary(run: StorageRun) {
    const summary = runSummariesByRunId.value[run.run_id];
    const succeededCount = summary?.succeeded_count ?? run.succeeded_count;
    const failedCount = summary?.failed_count ?? run.failed_count;
    const skippedCount = summary?.skipped_count ?? run.skipped_count;
    const totalCount = summary?.total_count ?? run.total_count;
    const totalBytesProcessed = summary?.total_bytes_processed ?? run.total_bytes_processed;
    const updateTime = summary?.update_time ?? run.update_time;
    const processed = succeededCount + failedCount + skippedCount;
    const progressPercent = totalCount > 0 ? Math.min(100, Math.round((processed / totalCount) * 100)) : 0;

    return {
        ...run,
        total_count: totalCount,
        succeeded_count: succeededCount,
        failed_count: failedCount,
        skipped_count: skippedCount,
        total_bytes_processed: totalBytesProcessed,
        update_time: updateTime,
        progressPercent,
    };
}

const tableRows = computed(() => {
    return trackedRuns.value.map(enrichRunWithSummary);
});

const filteredRows = computed(() => {
    const filter = filterText.value.trim().toLowerCase();
    if (!filter) {
        return tableRows.value;
    }

    return tableRows.value.filter((row) => {
        const haystack = [row.state, row.mode, row.target_object_store_id, row.total_count, row.create_time, row.run_id]
            .join(" ")
            .toLowerCase();
        return haystack.includes(filter);
    });
});

const displayRows = computed(() => {
    return [...filteredRows.value].sort((a, b) => {
        const aValue = getSortableValue(a);
        const bValue = getSortableValue(b);

        let comparison = 0;
        if (typeof aValue === "number" && typeof bValue === "number") {
            comparison = aValue - bValue;
        } else {
            comparison = String(aValue).localeCompare(String(bValue));
        }

        return sortDesc.value ? -comparison : comparison;
    });
});

const hasRuns = computed(() => tableRows.value.length > 0);

const historyName = computed(() => historyStore.getHistoryNameById(props.historyId));

const inProgressRows = computed(() => {
    return displayRows.value.filter((row) => !isTerminalRunState(row.state));
});

const finishedRows = computed(() => {
    return displayRows.value.filter((row) => isTerminalRunState(row.state));
});

const inProgressMaxPage = computed(() => {
    return Math.max(1, Math.ceil(inProgressRows.value.length / perPage));
});

const finishedMaxPage = computed(() => {
    return Math.max(1, Math.ceil(finishedRows.value.length / perPage));
});

function dismissStorageRun(runId: string) {
    storageOperationsStore.clearRun(runId);
}

function onSortChanged(newSortBy: string, newSortDesc: boolean) {
    sortBy.value = newSortBy;
    sortDesc.value = newSortDesc;
}

function getSortableValue(row: EnrichedStorageRun) {
    const key = sortBy.value;
    if (key === "create_time" || key === "update_time") {
        const val = key === "create_time" ? row.create_time : row.update_time;
        const timestamp = Date.parse(val);
        return Number.isNaN(timestamp) ? 0 : timestamp;
    }
    return row[key as keyof EnrichedStorageRun] ?? "";
}

onMounted(() => {
    startPolling();
});

onUnmounted(() => {
    stopPolling();
});

watch(displayRows, () => {
    if (inProgressPage.value > inProgressMaxPage.value) {
        inProgressPage.value = inProgressMaxPage.value;
    }
    if (finishedPage.value > finishedMaxPage.value) {
        finishedPage.value = finishedMaxPage.value;
    }
});

watch(filterText, () => {
    inProgressPage.value = 1;
    finishedPage.value = 1;
});

function onInProgressPageChange(page: number) {
    inProgressPage.value = page;
}

function onFinishedPageChange(page: number) {
    finishedPage.value = page;
}
</script>

<template>
    <div class="storage-operation-history-view">
        <Heading h2 separator size="md">{{ localize("History Storage Operations") }}</Heading>

        <p class="mb-3">
            {{ localize("Here you can track background storage operations related to the history") }}
            <strong>{{ historyName }}</strong>
            {{ localize(", such as moving or copying data across storage locations.") }}
        </p>

        <BAlert v-if="!hasRuns" show variant="secondary">
            {{ localize("No tracked storage operations for this history.") }}
        </BAlert>

        <template v-else>
            <div class="d-flex flex-wrap align-items-center mb-2 gap-2">
                <BFormInput
                    v-model="filterText"
                    class="storage-run-filter"
                    :placeholder="localize('Filter runs by target store location...')" />
            </div>

            <StorageOperationRunsTable
                :title="localize('In Progress')"
                :rows="inProgressRows"
                :current-page="inProgressPage"
                :per-page="perPage"
                :sort-by="sortBy"
                :sort-desc="sortDesc"
                :empty-message="localize('No in-progress runs found.')"
                pagination-class="mt-2 mb-3"
                @sort-changed="onSortChanged"
                @page-change="onInProgressPageChange"
                @dismiss="dismissStorageRun" />

            <StorageOperationRunsTable
                :title="localize('Finished')"
                :rows="finishedRows"
                :current-page="finishedPage"
                :per-page="perPage"
                :sort-by="sortBy"
                :sort-desc="sortDesc"
                :empty-message="localize('No finished runs found.')"
                heading-class="mt-3"
                pagination-class="mt-2"
                @sort-changed="onSortChanged"
                @page-change="onFinishedPageChange"
                @dismiss="dismissStorageRun" />
        </template>
    </div>
</template>

<style scoped>
.storage-run-filter {
    min-width: 280px;
    max-width: 520px;
}
</style>
