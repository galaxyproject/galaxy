<script setup lang="ts">
import { faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BFormCheckbox, BLink, BModal } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";

import { GalaxyApi, type HDASummary } from "@/api";
import { deleteDataset } from "@/api/datasets";
import { updateTags } from "@/api/tags";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { rethrowSimple } from "@/utils/simple-error";

import { useDatasetTableActions } from "./useDatasetTableActions";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import GTable from "@/components/Common/GTable.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
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

const historyStore = useHistoryStore();

const query = ref("");
const limit = ref(50);
const offset = ref(0);
const message = ref("");
const loading = ref(true);
const overlay = ref(false);
const loadMoreLoading = ref(false);
const sortDesc = ref(true);
const sortBy = ref("update_time");
const rows = ref<HDASummary[]>([]);
const messageVariant = ref("danger");
const selectedItemIds = ref<string[]>([]);
const hasMoreItems = ref(true);
const visibleColumns = ref<string[]>(["name", "tags", "history_id", "extension", "update_time"]);
const bulkDeleteLoading = ref(false);
const showDeleteModal = ref(false);
const deleteModalPurge = ref(false);
const deleteModalItem = ref<HDASummary | null>(null);
const deleteModalBulk = ref(false);

const { datasetTableActions } = useDatasetTableActions();

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
const deleteModalTitle = computed(() => {
    if (deleteModalBulk.value) {
        return `Delete ${selectedItemIds.value.length} dataset${selectedItemIds.value.length > 1 ? "s" : ""}?`;
    } else if (deleteModalItem.value) {
        return `Delete "${deleteModalItem.value.name}"?`;
    }
    return "Delete dataset?";
});
const deleteModalMessage = computed(() => {
    if (deleteModalBulk.value) {
        return `Are you sure you want to delete ${selectedItemIds.value.length} dataset${selectedItemIds.value.length > 1 ? "s" : ""}?`;
    } else if (deleteModalItem.value) {
        return `Are you sure you want to delete "${deleteModalItem.value.name}"?`;
    }
    return "Are you sure you want to delete this dataset?";
});

async function load(concat = false, showOverlay = false) {
    if (showOverlay) {
        overlay.value = true;
    } else if (concat) {
        loadMoreLoading.value = true;
    } else {
        loading.value = true;
    }

    try {
        const { data, error } = await GalaxyApi().GET("/api/datasets", {
            params: {
                query: {
                    q: ["name-contains"],
                    qv: [query.value],
                    limit: limit.value,
                    offset: offset.value,
                    order: `${sortBy.value}${sortDesc.value ? "-dsc" : "-asc"}`,
                    view: "summary",
                },
            },
        });

        if (error) {
            rethrowSimple(error);
        }

        const datasets = data as HDASummary[];

        if (concat) {
            rows.value = rows.value.concat(datasets);
        } else {
            rows.value = datasets;
        }

        hasMoreItems.value = datasets.length === limit.value;
    } catch (error: any) {
        onError(error);
    } finally {
        loading.value = false;
        overlay.value = false;
        loadMoreLoading.value = false;
    }
}

async function onShowDataset(item: HDASummary) {
    const { history_id } = item;
    const filters = {
        deleted: item.deleted,
        visible: item.visible,
        hid: item.hid,
    };

    try {
        await historyStore.applyFilters(history_id, filters);
    } catch (error: any) {
        onError(error);
    }
}

async function onTags(tags: string[], index: number) {
    const item = rows.value[index];

    if (item) {
        item.tags = tags;
    }

    try {
        await updateTags(item?.id as string, "HistoryDatasetAssociation", tags);
    } catch (error: any) {
        onError(error);
    }
}

function onQuery(q: string) {
    query.value = q;
    offset.value = 0;

    load();
}

function onSort(sortByValue: string, sortDescValue: boolean) {
    offset.value = 0;
    sortBy.value = sortByValue;
    sortDesc.value = sortDescValue;

    load(false, true);
}

function onScroll(scroll: Event) {
    const { scrollTop, clientHeight, scrollHeight } = scroll.target as HTMLElement;

    if (scrollTop + clientHeight >= scrollHeight) {
        if (offset.value + limit.value <= rows.value.length) {
            offset.value += limit.value;

            load(true);
        }
    }
}

function onError(msg: string) {
    message.value = msg;
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

function onBulkDelete() {
    deleteModalBulk.value = true;
    deleteModalItem.value = null;
    deleteModalPurge.value = false;
    showDeleteModal.value = true;
}

async function confirmDelete() {
    const purge = deleteModalPurge.value;

    try {
        overlay.value = true;

        if (deleteModalBulk.value) {
            const totalSelected = selectedItemIds.value.length;
            const tmpSelected = [...selectedItemIds.value];
            bulkDeleteLoading.value = true;

            for (const id of selectedItemIds.value) {
                await deleteDataset(id, purge);

                tmpSelected.splice(
                    tmpSelected.findIndex((s) => s === id),
                    1,
                );
            }

            Toast.success(
                `${purge ? "Permanently deleted" : "Deleted"} ${totalSelected} dataset${totalSelected > 1 ? "s" : ""}.`,
            );

            selectedItemIds.value = [];
            bulkDeleteLoading.value = false;
        } else if (deleteModalItem.value) {
            await deleteDataset(deleteModalItem.value.id, purge);
            Toast.success(`${purge ? "Permanently deleted" : "Deleted"} dataset "${deleteModalItem.value.name}".`);
        }

        await load(true);
    } catch (error: any) {
        Toast.error(`Failed to delete dataset${deleteModalBulk.value ? "s" : ""}.`);
        onError(error);
    } finally {
        overlay.value = false;
        showDeleteModal.value = false;
        deleteModalPurge.value = false;
        deleteModalItem.value = null;
        deleteModalBulk.value = false;
    }
}

function resetDeleteModal() {
    deleteModalPurge.value = false;
}

onMounted(() => {
    load();
});
</script>

<template>
    <div class="dataset-list-container h-100 d-flex flex-column">
        <BreadcrumbHeading :items="breadcrumbItems" />
        <div class="dataset-list-header">
            <BAlert v-if="message" :variant="messageVariant" show class="m-2">
                {{ message }}
            </BAlert>

            <DelayedInput class="m-2 mb-3" placeholder="Search Datasets" @change="onQuery" />

            <ListHeader
                list-id="datasets"
                :select-all-disabled="loading || rows.length === 0"
                :all-selected="allSelected"
                :indeterminate-selected="indeterminateSelected"
                :column-options="columnOptions"
                :visible-columns="visibleColumns"
                @select-all="onSelectAll"
                @toggle-column="onToggleColumn" />
        </div>

        <div v-if="loading" class="dataset-list-content">
            <BAlert variant="info" show>
                <LoadingSpan message="Loading datasets" />
            </BAlert>
        </div>
        <div v-else-if="showNotAvailable" class="dataset-list-content">
            <BAlert id="dataset-list-empty" variant="info" show>
                No datasets found. You may upload new datasets using the button above.
            </BAlert>
        </div>
        <div v-else-if="showNotFound" class="dataset-list-content">
            <BAlert id="no-dataset-found" variant="info" show>
                No matching entries found for: <span class="font-weight-bold">{{ query }}</span>
            </BAlert>
        </div>
        <div v-else class="dataset-list-content overflow-auto" @scroll="onScroll">
            <GTable
                id="dataset-table"
                striped
                selectable
                show-select-all
                no-sort-reset
                no-local-sorting
                :fields="fields"
                :items="rows"
                :sort-by="sortBy"
                :sort-desc="sortDesc"
                :overlay-loading="overlay"
                :load-more-loading="loadMoreLoading"
                :selected-items="selectedIndices"
                :actions="datasetTableActions"
                @sort-changed="onSort"
                @row-select="onRowSelect"
                @select-all="onSelectAll">
                <template v-slot:cell(name)="row">
                    <BLink
                        v-b-tooltip.hover.noninteractive
                        :title="localize('Show dataset in history panel')"
                        @click.stop.prevent="onShowDataset(row.item)">
                        {{ row.item.name }}
                    </BLink>
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

            <!-- End of list indicator -->
            <div v-if="!loadMoreLoading && rows.length > 0 && !hasMoreItems" class="text-center py-3 text-muted">
                - End of list -
            </div>
        </div>

        <!-- Bulk actions footer -->
        <div v-if="selectedItemIds.length > 0" class="d-flex mt-1 align-items-center">
            <div class="d-flex gap-1">
                <BButton
                    id="dataset-list-footer-bulk-delete-button"
                    v-b-tooltip.hover
                    :title="bulkDeleteLoading ? 'Deleting datasets' : 'Delete selected datasets'"
                    :disabled="bulkDeleteLoading"
                    size="sm"
                    variant="primary"
                    @click="onBulkDelete">
                    <span v-if="!bulkDeleteLoading">
                        <FontAwesomeIcon :icon="faTrash" fixed-width />
                        Delete ({{ selectedItemIds.length }})
                    </span>
                    <LoadingSpan v-else message="Deleting" />
                </BButton>
            </div>
        </div>

        <!-- Delete confirmation modal -->
        <BModal
            v-model="showDeleteModal"
            :title="deleteModalTitle"
            title-tag="h2"
            ok-title="Delete"
            ok-variant="danger"
            cancel-title="Cancel"
            cancel-variant="outline-primary"
            centered
            @show="resetDeleteModal"
            @ok="confirmDelete">
            <p>{{ deleteModalMessage }}</p>
            <BFormCheckbox id="purge-checkbox" v-model="deleteModalPurge">
                Permanently delete (cannot be recovered)
            </BFormCheckbox>
        </BModal>
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
