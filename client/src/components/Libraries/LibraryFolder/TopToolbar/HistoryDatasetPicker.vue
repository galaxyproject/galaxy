<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faHdd } from "@fortawesome/free-solid-svg-icons";
import { computed, ref } from "vue";

import { HDASummary, HistorySummary } from "@/api";
import { getDatasets } from "@/api/datasets";
import { postFolderContent } from "@/api/folders";
import { historiesFetcher } from "@/api/histories";
import { HistoriesFilters } from "@/components/History/HistoriesFilters";
import {
    ItemsProvider,
    ItemsProviderContext,
    SELECTION_STATES,
    SelectionItem,
} from "@/components/SelectionDialog/selectionTypes";
import { errorMessageAsString } from "@/utils/simple-error";

import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

library.add(faHdd);

type HistorySortKeys = "create_time" | "name" | "update_time" | undefined;

interface HistoryRecord extends SelectionItem {
    size: number;
}

interface Props {
    folderId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "reload"): void;
    (e: "onClose"): void;
}>();

const totalItems = ref(0);
const loading = ref(false);
const hasValue = ref(false);
const modalShow = ref(true);
const errorMessage = ref("");
const allSelected = ref(false);
const datasetsVisible = ref(false);

const items = ref<SelectionItem[]>([]);
const selected = ref<SelectionItem[]>([]);

const itemsProvider = ref<ItemsProvider>(historiesProvider);

const searchTitle = computed(() => {
    if (datasetsVisible.value) {
        return "datasets";
    } else {
        return "search histories";
    }
});
const okButtonText = computed(() => {
    if (selected.value.length === 0) {
        return "Add";
    }

    return `Add ${selected.value.length} dataset${selected.value.length > 1 ? "s" : ""}`;
});
const fields = computed(() => {
    if (datasetsVisible.value) {
        return [
            { key: "label", label: "Name", sortable: true },
            { key: "update_time", label: "Last Updated", sortable: true },
        ];
    } else {
        return [
            { key: "label", label: "History Name" },
            { key: "size", label: "Datasets", sortable: false },
            { key: "update_time", label: "Last Updated" },
        ];
    }
});
const selectAllIcon = computed(() => {
    if (allSelected.value) {
        return SELECTION_STATES.SELECTED;
    } else if (selected.value.length > 0) {
        return SELECTION_STATES.MIXED;
    } else {
        return SELECTION_STATES.UNSELECTED;
    }
});

function historyEntryToRecord(entry: HistorySummary): HistoryRecord {
    const result = {
        id: entry.id,
        label: entry.name,
        details: entry.annotation || "",
        isLeaf: false,
        url: entry.url,
        size: entry.count,
        update_time: entry.update_time,
    };

    return result;
}

function datasetEntryToRecord(entry: HDASummary): SelectionItem {
    const result = {
        id: entry.id,
        label: entry.name || "",
        details: "",
        isLeaf: true,
        url: entry.url,
        update_time: entry.update_time,
    };

    return result;
}

function formatRows() {
    hasValue.value = selected.value.length > 0;

    for (const item of items.value) {
        if (item.isLeaf) {
            item._rowVariant =
                selected.value.findIndex((i) => i.id === item.id) !== -1
                    ? SELECTION_STATES.SELECTED
                    : SELECTION_STATES.UNSELECTED;
        }
    }

    allSelected.value = checkIfAllSelected();
}

function checkIfAllSelected(): boolean {
    return Boolean(
        items.value.length &&
            items.value.every((item) => {
                return selected.value.findIndex((i) => i.id === item.id) !== -1;
            })
    );
}

async function historiesProvider(ctx: ItemsProviderContext, url?: string): Promise<SelectionItem[]> {
    loading.value = true;

    try {
        const limit = ctx.perPage;
        const offset = (ctx.currentPage - 1) * ctx.perPage;
        const sortDesc = ctx.sortDesc;
        const sortBy = ctx.sortBy === "label" ? "name" : ctx.sortBy || "update_time";
        const queryDict = HistoriesFilters.getQueryDict(ctx.filter);

        const { data, headers } = await historiesFetcher({
            search: "",
            view: "summary",
            keys: "create_time",
            offset: offset,
            limit: limit,
            q: Object.keys(queryDict),
            qv: Object.values(queryDict),
            sort_by: sortBy as HistorySortKeys,
            sort_desc: sortDesc,
        });

        totalItems.value = parseInt(headers.get("total_matches") ?? "0");

        items.value = data.map(historyEntryToRecord as any);

        formatRows();

        return items.value;
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
        return [];
    } finally {
        loading.value = false;
    }
}

async function datasetsProvider(ctx: ItemsProviderContext, selectedHistory: HistoryRecord) {
    loading.value = true;

    try {
        const limit = ctx.perPage;
        const offset = (ctx.currentPage - 1) * ctx.perPage;
        const query = ctx.filter;

        const data = await getDatasets({
            history_id: selectedHistory.id,
            query: query,
            sortBy: ctx.sortBy === "time" ? "update_time" : "name",
            sortDesc: ctx.sortDesc,
            offset: offset,
            limit: limit,
        });

        items.value = (data as HDASummary[]).map(datasetEntryToRecord);

        if (query) {
            totalItems.value = items.value.length;
        } else {
            totalItems.value = selectedHistory.size;
        }

        formatRows();

        return items.value;
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);

        return [];
    } finally {
        loading.value = false;
    }
}

function onHistoryClick(item: SelectionItem) {
    if (!item.isLeaf) {
        datasetsVisible.value = true;
        itemsProvider.value = (ctx: ItemsProviderContext) => datasetsProvider(ctx, item as HistoryRecord);
    }
}

async function onDatasetClick(item: SelectionItem) {
    if (item.isLeaf) {
        if (selected.value.findIndex((i) => i.id === item.id) !== -1) {
            selected.value = selected.value.filter((i) => i.id !== item.id);
        } else {
            selected.value.push(item);
        }

        formatRows();
    }
}

function selectAll() {
    if (allSelected.value) {
        selected.value = [];
    } else {
        for (const item of items.value) {
            if (selected.value.findIndex((i) => i.id === item.id) === -1) {
                selected.value.push(item);
            }
        }
    }

    formatRows();
}

async function onUndo() {
    selected.value = [];
    datasetsVisible.value = false;
    itemsProvider.value = historiesProvider;
}

async function onOk() {
    for (const item of selected.value) {
        await postFolderContent({ folder_id: props.folderId, from_hda_id: item.id });
    }

    emit("reload");
    emit("onClose");
}

function onCancel() {
    modalShow.value = false;

    emit("onClose");
}
</script>

<template>
    <SelectionDialog
        options-show
        :disable-ok="!hasValue"
        :fields="fields"
        :ok-button-text="okButtonText"
        :modal-show="modalShow"
        :file-mode="false"
        :multiple="true"
        :select-all-variant="selectAllIcon"
        :items="items"
        :undo-show="datasetsVisible"
        :total-items="totalItems"
        :items-provider="itemsProvider"
        :show-select-icon="datasetsVisible"
        :folder-icon="faHdd"
        :is-busy="loading"
        :search-title="searchTitle"
        title="Add datasets from your histories"
        :filter-class="datasetsVisible ? undefined : HistoriesFilters"
        @onOk="onOk"
        @onUndo="onUndo"
        @onCancel="onCancel"
        @onSelectAll="selectAll"
        @onOpen="onHistoryClick"
        @onClick="onDatasetClick" />
</template>
