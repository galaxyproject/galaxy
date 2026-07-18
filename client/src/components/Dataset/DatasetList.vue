<script setup lang="ts">
import { faBurn, faCheckCircle, faCopy, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BPagination } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import type { HDASummary, HistorySummary } from "@/api";
import { copyDatasets, deleteDataset, loadDatasets } from "@/api/datasets";
import { updateTags } from "@/api/tags";
import type { RowIcon } from "@/components/Common/GTable.types";
import { STATES } from "@/components/History/Content/model/states";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";

import { useDatasetTableActions } from "./useDatasetTableActions";

import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import GTable from "@/components/Common/GTable.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import SelectorModal from "@/components/History/Modals/SelectorModal.vue";
import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";

const breadcrumbItems = [{ title: "Datasets", to: "/datasets/list" }];

const allFields = [
    {
        key: "name",
        label: "Name",
        sortable: true,
    },
    {
        key: "tags",
        label: "Tags",
        sortable: false,
    },
    {
        key: "history_id",
        label: "History",
        sortable: true,
    },
    {
        key: "extension",
        label: "Extension",
        sortable: true,
    },
    {
        key: "update_time",
        label: "Updated",
        sortable: true,
    },
];

const columnOptions = allFields.map((field) => ({ key: field.key, label: field.label }));

const { confirm } = useConfirmDialog();

const query = ref("");
const limit = ref(24);
const offset = ref(0);
const loading = ref(true);
const overlay = ref(false);
const sortDesc = ref(true);
const sortBy = ref("update_time");
const rows = ref<HDASummary[]>([]);
const selectedItemIds = ref<string[]>([]);
const totalDatasets = ref(0);
const visibleColumns = ref<string[]>(["name", "tags", "history_id", "extension", "update_time"]);
const bulkDeleteOrRestoreLoading = ref(false);
const bulkCopyLoading = ref(false);
const showBulkCopyModal = ref(false);

const { datasetTableActions } = useDatasetTableActions(() => load(true));
const historyStore = useHistoryStore();
const { currentHistoryId, histories } = storeToRefs(historyStore);

const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1);
const fields = computed(() => allFields.filter((field) => visibleColumns.value.includes(field.key)));
const showNotFound = computed(() => {
    return !loading.value && rows.value.length === 0 && query.value;
});
const showNotAvailable = computed(() => {
    return !loading.value && rows.value.length === 0 && !query.value;
});
const allSelected = computed(() => {
    return rows.value.length > 0 && selectedItemIds.value.length === rows.value.length;
});
const indeterminateSelected = computed(() => {
    return selectedItemIds.value.length > 0 && selectedItemIds.value.length < rows.value.length;
});
const selectedIndices = computed(() => {
    return rows.value
        .map((row, index) => (selectedItemIds.value.includes(row.id) ? index : -1))
        .filter((i) => i !== -1);
});
async function load(showOverlay = false) {
    if (showOverlay) {
        overlay.value = true;
    } else {
        loading.value = true;
    }

    try {
        const { data, totalMatches } = await loadDatasets({
            limit: limit.value,
            offset: offset.value,
            sortBy: sortBy.value,
            sortDesc: sortDesc.value,
            search: query.value,
        });

        rows.value = data;
        totalDatasets.value = totalMatches;
    } catch (e: any) {
        Toast.error(`Failed to load datasets: ${e}`);
    } finally {
        loading.value = false;
        overlay.value = false;
    }
}

async function onTags(tags: string[], index: number) {
    const item = rows.value[index];

    if (item) {
        item.tags = tags;
    }

    try {
        await updateTags(item?.id as string, "HistoryDatasetAssociation", tags);
    } catch (e: any) {
        Toast.error(`Failed to update tags: ${e}`);
    }
}

function onQuery(q: string) {
    query.value = q;
    offset.value = 0;
    selectedItemIds.value = [];
    load();
}

function onSort(sortByValue: string, sortDescValue: boolean) {
    offset.value = 0;
    sortBy.value = sortByValue;
    sortDesc.value = sortDescValue;
    selectedItemIds.value = [];
    load(true);
}

async function onPageChange(page: number) {
    offset.value = (page - 1) * limit.value;
    selectedItemIds.value = [];
    await load(true);
}

function onSelectAll() {
    if (allSelected.value) {
        selectedItemIds.value = [];
    } else {
        selectedItemIds.value = rows.value.map((row) => row.id);
    }
}

function onRowSelect(event: { item: HDASummary; index: number; selected: boolean }) {
    const index = selectedItemIds.value.indexOf(event.item.id);
    if (index > -1) {
        selectedItemIds.value.splice(index, 1);
    } else {
        selectedItemIds.value.push(event.item.id);
    }
}

function onResetColumns() {
    visibleColumns.value = allFields.map((field) => field.key);
}

function onToggleColumn(key: string) {
    const index = visibleColumns.value.indexOf(key);
    if (index > -1) {
        if (visibleColumns.value.length > 1 && key !== "name") {
            visibleColumns.value.splice(index, 1);
        }
    } else {
        visibleColumns.value.push(key);
    }
}

async function onBulkDelete() {
    const totalSelected = selectedItemIds.value.length;

    const confirmed = await confirm(`Are you sure you want to delete ${totalSelected} datasets?`, {
        title: "Delete datasets",
        okText: "Delete datasets",
        okColor: "red",
        okIcon: faTrash,
    });

    if (confirmed) {
        try {
            overlay.value = true;
            bulkDeleteOrRestoreLoading.value = true;

            const totalSelected = selectedItemIds.value.length;
            const tmpSelected = [...selectedItemIds.value];

            for (const id of selectedItemIds.value) {
                await deleteDataset(id);

                tmpSelected.splice(
                    tmpSelected.findIndex((s) => s === id),
                    1,
                );
            }

            Toast.success(`Deleted ${totalSelected} dataset${totalSelected > 1 ? "s" : ""}.`);

            selectedItemIds.value = [];
        } catch (e: any) {
            Toast.error(`Failed to delete some datasets: ${e}`);
        } finally {
            overlay.value = false;
            bulkDeleteOrRestoreLoading.value = false;

            await load(true);
        }
    }
}

function openBulkCopyModal() {
    if (!currentHistoryId.value) {
        Toast.error("No current history found.");
        return;
    }

    showBulkCopyModal.value = true;
}

async function onBulkCopy(targetHistory: HistorySummary) {
    const datasetIdsToCopy = [...selectedItemIds.value];
    const totalSelected = datasetIdsToCopy.length;

    try {
        overlay.value = true;
        bulkCopyLoading.value = true;

        const { copiedDatasets, failedDatasetIds } = await copyDatasets(datasetIdsToCopy, targetHistory.id);

        const copiedCount = copiedDatasets.length;
        const failedCount = failedDatasetIds.length;

        if (failedCount === 0) {
            Toast.success(`Copied ${copiedCount} dataset${copiedCount !== 1 ? "s" : ""} to ${targetHistory.name}.`);
            selectedItemIds.value = [];
        } else if (copiedCount > 0) {
            Toast.error(
                `Copied ${copiedCount} of ${totalSelected} dataset${totalSelected !== 1 ? "s" : ""}. Failed to copy ${failedCount} dataset${failedCount !== 1 ? "s" : ""}.`,
            );
            selectedItemIds.value = failedDatasetIds;
        } else {
            // Keep original selection so the user can retry the failed copy.
            Toast.error(`Failed to copy ${totalSelected} dataset${totalSelected !== 1 ? "s" : ""}.`);
        }
    } catch (e: any) {
        Toast.error(`Failed to copy datasets: ${e?.message ?? String(e)}`);
    } finally {
        bulkCopyLoading.value = false;

        await load(true);
    }
}

function getDatasetStatusIcon(item: HDASummary): RowIcon | undefined {
    if (item.purged) {
        return { icon: faBurn, class: "text-danger", title: "Purged" };
    }
    if (item.deleted) {
        return { icon: faTrash, class: "text-muted", title: "Deleted" };
    }
    if (item.state === "ok") {
        return { icon: faCheckCircle, class: "text-success", title: "Success" };
    }
    const state = item.state && STATES[item.state];
    if (state?.icon) {
        return {
            icon: state.icon,
            class: `text-${state.status}`,
            title: state.displayName,
            spin: state.spin,
        };
    }
    return undefined;
}

onMounted(() => {
    load();
});
</script>

<template>
    <div class="dataset-list-container h-100 d-flex flex-column">
        <BreadcrumbHeading :items="breadcrumbItems" />
        <div class="dataset-list-header">
            <DelayedInput class="m-2 mb-3" placeholder="Search Datasets" @change="onQuery" />

            <ListHeader
                list-id="datasets"
                :select-all-disabled="loading || rows.length === 0"
                :all-selected="allSelected"
                :indeterminate-selected="indeterminateSelected"
                :column-options="columnOptions"
                :visible-columns="visibleColumns"
                @select-all="onSelectAll"
                @reset-columns="onResetColumns"
                @toggle-column="onToggleColumn" />
        </div>

        <div v-if="loading" class="dataset-list-content">
            <GAlert variant="info" show>
                <LoadingSpan message="Loading datasets" />
            </GAlert>
        </div>
        <div v-else-if="showNotAvailable" class="dataset-list-content">
            <GAlert id="dataset-list-empty" variant="info" show>
                No datasets found. You may upload new datasets using the button above.
            </GAlert>
        </div>
        <div v-else-if="showNotFound" class="dataset-list-content">
            <GAlert id="no-dataset-found" variant="info" show>
                No matching entries found for: <span class="font-weight-bold">{{ query }}</span>
            </GAlert>
        </div>
        <div v-else class="dataset-list-content overflow-auto">
            <GTable
                id="dataset-table"
                striped
                selectable
                show-select-all
                no-sort-reset
                :local-sorting="false"
                :fields="fields"
                :items="rows"
                :sort-by="sortBy"
                :sort-desc="sortDesc"
                :overlay-loading="overlay"
                :selected-items="selectedIndices"
                :actions="datasetTableActions"
                :status-icon="getDatasetStatusIcon"
                @sort-changed="onSort"
                @row-select="onRowSelect"
                @select-all="onSelectAll">
                <template v-slot:cell(name)="row">
                    <span>{{ row.item.name }}</span>
                </template>

                <template v-slot:cell(history_id)="row">
                    <SwitchToHistoryLink
                        :history-id="row.item.history_id"
                        :filters="{
                            deleted: row.item.deleted,
                            visible: row.item.visible,
                            hid: String(row.item.hid),
                        }" />
                </template>

                <template v-slot:cell(tags)="row">
                    <StatelessTags
                        :value="row.item.tags"
                        :disabled="row.item.deleted"
                        @input="(tags) => onTags(tags, row.index)" />
                </template>

                <template v-slot:cell(update_time)="data">
                    <UtcDate :date="data.value" mode="elapsed" />
                </template>
            </GTable>
        </div>

        <div class="d-flex mt-1 align-items-center mt-2">
            <div v-if="selectedItemIds.length > 0" class="d-flex gap-1 w-100 position-absolute">
                <GButton
                    id="dataset-list-footer-bulk-copy-button"
                    tooltip
                    size="small"
                    color="blue"
                    :disabled="bulkCopyLoading || bulkDeleteOrRestoreLoading"
                    :title="bulkCopyLoading ? 'Copying datasets' : 'Copy selected datasets'"
                    @click="openBulkCopyModal">
                    <FontAwesomeIcon :icon="faCopy" />
                    {{ localize("Copy Selected") }} ({{ selectedItemIds.length }})
                </GButton>

                <BButton
                    id="dataset-list-footer-bulk-delete-button"
                    v-g-tooltip.hover
                    size="sm"
                    variant="primary"
                    :disabled="bulkDeleteOrRestoreLoading || bulkCopyLoading"
                    :title="bulkDeleteOrRestoreLoading ? 'Deleting datasets' : 'Delete selected datasets'"
                    @click="onBulkDelete">
                    <FontAwesomeIcon :icon="faTrash" />
                    {{ localize("Delete Selected") }} ({{ selectedItemIds.length }})
                </BButton>
            </div>

            <BPagination
                class="mx-0 my-auto w-100"
                :value="currentPage"
                :total-rows="totalDatasets"
                :per-page="limit"
                align="right"
                size="sm"
                first-number
                last-number
                @change="onPageChange" />
        </div>

        <SelectorModal
            :histories="histories"
            hide-deleted
            :show-modal.sync="showBulkCopyModal"
            title="Copy selected datasets to history"
            selection-instruction="Click a history to copy selected datasets"
            @selectHistory="onBulkCopy" />
    </div>
</template>

<style scoped lang="scss">
.dataset-list-container {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.dataset-list-header {
    flex-shrink: 0;
}

.dataset-list-content {
    flex: 1;
    overflow-y: auto;
}

.dataset-list-footer {
    flex-shrink: 0;
    padding: 0.5rem 1rem;
    background-color: #f8f9fa;
    border-top: 1px solid #dee2e6;
}

.gap-1 {
    gap: 0.25rem;
}
</style>
