<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faCaretLeft, faFolder } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BPagination } from "bootstrap-vue";

import type { TableField } from "@/components/Common/GTable.types";
import type { SelectionItem, SelectItemsProvider } from "@/components/SelectionDialog/selectionTypes";
import { type SelectItemsState, useSelectItems } from "@/composables/useSelectItems";
import type Filtering from "@/utils/filtering";

import GButton from "@/components/BaseComponents/GButton.vue";
import SelectionList from "@/components/SelectionDialog/SelectionList.vue";
import SelectionSearch from "@/components/SelectionDialog/SelectionSearch.vue";

interface Props {
    fields?: TableField[];
    filterClass?: Filtering<any>;
    folderIcon?: IconDefinition;
    isEncoded?: boolean;
    leafIcon?: string;
    /** Data source; the panel loads, pages, searches and navigates through it. */
    provider?: SelectItemsProvider;
    searchTitle?: string;
    selectable?: boolean;
    /** Caller-owned useSelectItems() state, for callers that read the path or selection themselves. */
    state?: SelectItemsState;
}

const props = withDefaults(defineProps<Props>(), {
    fields: () => [],
    filterClass: undefined,
    folderIcon: () => faFolder,
    isEncoded: false,
    leafIcon: "fa fa-file-o",
    provider: undefined,
    searchTitle: "",
    selectable: false,
    state: undefined,
});

const emit = defineEmits<{
    (e: "back"): void;
    (e: "click", item: SelectionItem): void;
    (e: "open", item: SelectionItem): void;
}>();

const EMPTY_PROVIDER: SelectItemsProvider = {
    load: async () => ({ items: [] }),
    map: (raw) => raw as SelectionItem,
};

if (process.env.NODE_ENV !== "production" && !props.state && !props.provider) {
    console.warn("SelectionPanel needs a provider or state; it shows an empty list.");
}

const selection = props.state ?? useSelectItems(() => props.provider ?? EMPTY_PROVIDER);
const { error, filter, items, loaded, loading, page, path, perPage, total } = selection;

function onSortChanged(key: string, desc: boolean) {
    selection.setSort(key, desc, props.fields.find((field) => field.key === key)?.formatter);
}

function onBack() {
    selection.back();
    emit("back");
}

function onClick(item: SelectionItem) {
    if (props.selectable) {
        selection.toggle(item);
    }
    emit("click", item);
}

function onOpen(item: SelectionItem) {
    selection.open(item);
    emit("open", item);
}
</script>

<template>
    <div class="d-flex flex-column">
        <SelectionSearch
            v-model:filter="filter"
            :filter-class="props.filterClass"
            :loading="loading"
            :placeholder="props.searchTitle" />
        <SelectionList
            :error-message="error"
            :fields="props.fields"
            :filter="filter"
            :folder-icon="props.folderIcon"
            :is-busy="loading"
            :is-encoded="props.isEncoded"
            :items="items"
            :leaf-icon="props.leafIcon"
            :options-show="loaded"
            :selectable="props.selectable"
            :total-items="total"
            @click="onClick"
            @open="onOpen"
            @select-all="selection.selectAll"
            @sort-changed="onSortChanged" />
        <div class="d-flex justify-content-between">
            <GButton v-if="path.length > 0" data-description="selection panel back" size="small" @click="onBack">
                <FontAwesomeIcon :icon="faCaretLeft" />
                Back
            </GButton>
            <BPagination
                v-if="total > perPage"
                v-model="page"
                class="justify-content-md-center m-0"
                size="sm"
                :per-page="perPage"
                :total-rows="total" />
        </div>
    </div>
</template>
