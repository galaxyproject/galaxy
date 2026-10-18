<script setup lang="ts">
import { faHdd } from "@fortawesome/free-solid-svg-icons";
import { computed, ref } from "vue";

import { GalaxyApi, type HDASummary, type HistorySortByLiteral, type HistorySummary } from "@/api";
import { getMyHistories } from "@/api/histories";
import type { TableField } from "@/components/Common/GTable.types";
import { HistoriesFilters } from "@/components/History/HistoriesFilters";
import { datasetToItem, historyToItem } from "@/components/SelectionDialog/selectionAdapters";
import type { SelectionItem, SelectItemsProvider, SelectItemsQuery } from "@/components/SelectionDialog/selectionTypes";
import { useSelectItems } from "@/composables/useSelectItems";

import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

interface Props {
    title?: string;
    actionButtonText?: string;
}

const props = withDefaults(defineProps<Props>(), {
    title: "Select datasets from your histories",
    actionButtonText: "Select",
});

const emit = defineEmits<{
    (e: "reload"): void;
    (e: "onClose"): void;
    (e: "onSelect", datasets: SelectionItem[]): void;
}>();

const modalShow = ref(true);

/** Histories at the root level, the datasets of the opened history one level down. */
const provider: SelectItemsProvider<HistorySummary | HDASummary> = {
    load: (query) => (query.path[0] ? loadDatasets(query, query.path[0].id) : loadHistories(query)),
    map: (raw, query) => (query.path.length ? datasetToItem(raw as HDASummary) : historyToItem(raw as HistorySummary)),
};

const state = useSelectItems(provider);
const { selected } = state;

const datasetsVisible = computed(() => state.path.value.length > 0);

const searchTitle = computed(() => {
    if (datasetsVisible.value) {
        return "datasets";
    } else {
        return "search histories";
    }
});
const okButtonText = computed(() => {
    if (selected.value.length === 0) {
        return props.actionButtonText;
    } else {
        return `${props.actionButtonText} ${selected.value.length} dataset${selected.value.length > 1 ? "s" : ""}`;
    }
});

const fields = computed<TableField[]>(() => {
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

async function loadHistories(query: SelectItemsQuery) {
    const sortBy: HistorySortByLiteral =
        query.sortBy === "label" ? "name" : (query.sortBy as HistorySortByLiteral) || "update_time";

    const { data, total } = await getMyHistories({
        limit: query.perPage,
        offset: (query.page - 1) * query.perPage,
        search: query.filter,
        sortBy,
        sortDesc: query.sortDesc ?? true,
    });

    return { items: data, total };
}

async function loadDatasets(query: SelectItemsQuery, historyId: string) {
    const querySortBy = query.sortBy === "time" ? "update_time" : "name";
    const sortPrefix = query.sortDesc ? "-dsc" : "-asc";

    const { response, data, error } = await GalaxyApi().GET("/api/datasets", {
        params: {
            query: {
                history_id: historyId,
                q: ["name-contains"],
                qv: [query.filter],
                order: `${querySortBy}${sortPrefix}`,
                offset: (query.page - 1) * query.perPage,
                limit: query.perPage,
            },
        },
        signal: query.signal,
    });

    if (error) {
        throw error;
    }

    return { items: data as HDASummary[], total: parseInt(response.headers.get("total_matches") ?? "0") };
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
        :disable-ok="selected.length === 0"
        :fields="fields"
        :ok-button-text="okButtonText"
        :modal-show="modalShow"
        :file-mode="false"
        :multiple="true"
        :selectable="datasetsVisible"
        :state="state"
        :folder-icon="faHdd"
        :search-title="searchTitle"
        :title="title"
        :filter-class="datasetsVisible ? undefined : HistoriesFilters"
        @onOk="onOk"
        @onUndo="state.clearSelection()"
        @onCancel="onCancel" />
</template>
