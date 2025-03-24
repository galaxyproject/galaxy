<script setup lang="ts">
import { faHdd } from "@fortawesome/free-solid-svg-icons";
import { computed, ref, set } from "vue";

import { GalaxyApi, type HDASummary, type HistorySortByLiteral, type HistorySummary } from "@/api";
import { HistoriesFilters } from "@/components/History/HistoriesFilters";
import {
    type ItemsProvider,
    type ItemsProviderContext,
    SELECTION_STATES,
    type SelectionItem,
} from "@/components/SelectionDialog/selectionTypes";
import { errorMessageAsString } from "@/utils/simple-error";

import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

interface HistoryRecord extends SelectionItem {
    size: number;
}

interface Props {
    folderId: string;
    title?: string;
    actionButtonText?: string;
}
const props = withDefaults(defineProps<Props>(), {
    title: "从您的历史记录中选择数据集",
    actionButtonText: "选择",
});

const emit = defineEmits<{
    (e: "reload"): void;
    (e: "onClose"): void;
    (e: "onSelect", datasets: SelectionItem[]): void;
}>();

const selectionDialog = ref();

const totalItems = ref(0);
const loading = ref(false);
const hasValue = ref(false);
const modalShow = ref(true);
const errorMessage = ref("");
const submitting = ref(false);
const allSelected = ref(false);
const datasetsVisible = ref(false);

const items = ref<SelectionItem[]>([]);
const selected = ref<SelectionItem[]>([]);

const itemsProvider = ref<ItemsProvider>(historiesProvider);
const searchTitle = computed(() => {
    if (datasetsVisible.value) {
        return "数据集";
    } else {
        return "搜索历史记录";
    }
});
const okButtonText = computed(() => {
    if (selected.value.length === 0) {
        return props.actionButtonText;
    } else {
        return `${props.actionButtonText} ${selected.value.length} 个数据集`;
    }
});
const fields = computed(() => {
    if (datasetsVisible.value) {
        return [
            { key: "label", label: "名称", sortable: true },
            { key: "update_time", label: "最后更新", sortable: true },
        ];
    } else {
        return [
            { key: "label", label: "历史记录名称" },
            { key: "size", label: "数据集", sortable: false },
            { key: "update_time", label: "最后更新" },
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
            const _rowVariant =
                selected.value.findIndex((i) => i.id === item.id) !== -1
                    ? SELECTION_STATES.SELECTED
                    : SELECTION_STATES.UNSELECTED;

            set(item, "_rowVariant", _rowVariant);
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
        const filter = ctx.filter;

        if (filter) {
            selectionDialog.value?.resetPagination();
        }

        const limit = ctx.perPage;
        const offset = (ctx.currentPage ? ctx.currentPage - 1 : 0) * ctx.perPage;
        const sortDesc = ctx.sortDesc;
        const sortBy: HistorySortByLiteral =
            ctx.sortBy === "label" ? "name" : (ctx.sortBy as HistorySortByLiteral) || "update_time";
        const queryDict = HistoriesFilters.getQueryDict(ctx.filter);

        const { response, data, error } = await GalaxyApi().GET("/api/histories", {
            params: {
                query: {
                    search: filter,
                    view: "summary",
                    keys: "create_time",
                    show_own: true,
                    offset: offset,
                    limit: limit,
                    q: Object.keys(queryDict),
                    qv: Object.values(queryDict),
                    sort_by: sortBy,
                    sort_desc: sortDesc,
                },
            },
        });

        if (error) {
            errorMessage.value = errorMessageAsString(error);
            return [];
        }

        totalItems.value = parseInt(response.headers.get("total_matches") ?? "0");

        items.value = (data as HistorySummary[]).map(historyEntryToRecord);

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
        const offset = (ctx.currentPage ? ctx.currentPage - 1 : 0) * ctx.perPage;
        const query = ctx.filter || "";
        const querySortBy = ctx.sortBy === "time" ? "update_time" : "name";
        const sortPrefix = ctx.sortDesc ? "-dsc" : "-asc";

        const { response, data, error } = await GalaxyApi().GET("/api/datasets", {
            params: {
                query: {
                    history_id: selectedHistory.id,
                    q: ["name-contains"],
                    qv: [query],
                    order: `${querySortBy}${sortPrefix}`,
                    offset: offset,
                    limit: limit,
                },
            },
        });

        if (error) {
            errorMessage.value = errorMessageAsString(error);
            return [];
        }

        totalItems.value = parseInt(response.headers.get("total_matches") ?? "0");

        items.value = (data as HDASummary[]).map(datasetEntryToRecord);

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
        selectionDialog.value?.resetFilter();
        selectionDialog.value?.resetPagination();
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
    selectionDialog.value?.resetFilter();
    selectionDialog.value?.resetPagination();
    selected.value = [];
    datasetsVisible.value = false;
    itemsProvider.value = historiesProvider;
}

function onOk() {
    emit("onSelect", selected.value);
    emit("onClose");
}

function onCancel() {
    modalShow.value = false;

    emit("onClose");
}
</script>

<template>
    <SelectionDialog
        ref="selectionDialog"
        options-show
        :disable-ok="!hasValue || submitting"
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
        :title="title"
        :filter-class="datasetsVisible ? undefined : HistoriesFilters"
        @onOk="onOk"
        @onUndo="onUndo"
        @onCancel="onCancel"
        @onSelectAll="selectAll"
        @onOpen="onHistoryClick"
        @onClick="onDatasetClick" />
</template>
