<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faCaretLeft, faCheck, faFolder, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BLink, BPagination, BSpinner } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { RowClickEvent, TableField } from "@/components/Common/GTable.types";
import { type ItemsProvider, SELECTION_STATES } from "@/components/SelectionDialog/selectionTypes";
import type Filtering from "@/utils/filtering";

import type { SelectionItem } from "./selectionTypes";

import GModal from "../BaseComponents/GModal.vue";
import Heading from "../Common/Heading.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import GTable from "@/components/Common/GTable.vue";
import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

const LABEL_FIELD: TableField = { key: "label", label: "Name", sortable: true };

interface Props {
    disableOk?: boolean;
    errorMessage?: string;
    fileMode?: boolean;
    fields?: TableField[];
    isBusy?: boolean;
    isEncoded?: boolean;
    items?: SelectionItem[];
    itemsProvider?: ItemsProvider;
    providerUrl?: string;
    totalItems?: number;
    leafIcon?: string;
    folderIcon?: IconDefinition;
    modalShow?: boolean;
    multiple?: boolean;
    optionsShow?: boolean;
    undoShow?: boolean;
    selectable?: boolean;
    allSelected?: boolean;
    title?: string;
    searchTitle?: string;
    okButtonText?: string;
    filterClass?: Filtering<any>;
    watchOnPageChanges?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    disableOk: false,
    errorMessage: "",
    fileMode: true,
    fields: () => [],
    isBusy: false,
    isEncoded: false,
    items: () => [],
    itemsProvider: undefined,
    providerUrl: undefined,
    totalItems: 0,
    leafIcon: "fa fa-file-o",
    folderIcon: () => faFolder,
    modalShow: true,
    multiple: false,
    optionsShow: false,
    undoShow: false,
    selectable: false,
    allSelected: undefined,
    title: "",
    searchTitle: undefined,
    okButtonText: "Select",
    filterClass: undefined,
    watchOnPageChanges: true,
});

const emit = defineEmits<{
    (e: "onCancel"): void;
    (e: "onClick", record: SelectionItem): void;
    (e: "onOk"): void;
    (e: "onOpen", record: SelectionItem): void;
    (e: "onSelectAll"): void;
    (e: "onUndo"): void;
}>();

const filter = ref("");
const currentPage = ref(1);
const perPage = ref(25);
const showAdvancedSearch = ref(false);
const selectedItems = ref<number[]>([]);

const providerRequestId = ref(0);
const providerItems = ref<SelectionItem[]>([]);
const sortBy = ref<string | undefined>(undefined);
const sortDesc = ref<boolean | undefined>(undefined);

const usingProvider = computed(() => Boolean(props.itemsProvider));

const okButtonText = computed(() => {
    return props.okButtonText ? props.okButtonText : props.fileMode ? "Select" : "Select this folder";
});

const fieldDetails = computed<TableField[]>(() => {
    const fields: TableField[] = props.fields.slice().map((field) => ({
        ...field,
        sortable: field.sortable ?? true,
    }));
    if (fields.length === 0) {
        fields.unshift(LABEL_FIELD);
    }
    return fields;
});

/**
 * Sync selectedItems based on item classes/selection state.
 * Updates the selected items array whenever the items change.
 */
function syncSelectedItems() {
    selectedItems.value = tableItems.value
        .map((item, index) => {
            const hasClass = (item as any)?.class === "table-success";
            const isSelected = (item as any)?.selectionState === SELECTION_STATES.SELECTED;
            return hasClass || isSelected ? index : -1;
        })
        .filter((index) => index !== -1);
}

const tableItems = computed(() => {
    return usingProvider.value ? providerItems.value : props.items;
});

async function loadProviderItems() {
    if (!props.itemsProvider || !props.optionsShow) {
        return;
    }

    const requestId = ++providerRequestId.value;
    const result = await props.itemsProvider({
        apiUrl: props.providerUrl,
        currentPage: currentPage.value,
        perPage: perPage.value,
        filter: filter.value || undefined,
        sortBy: sortBy.value,
        sortDesc: sortDesc.value,
    });

    if (requestId === providerRequestId.value) {
        providerItems.value = result ?? [];
    }
}

function onSortChanged(newSortBy: string, newSortDesc: boolean) {
    sortBy.value = newSortBy || undefined;
    sortDesc.value = newSortDesc;
}

function onRowClick(event: RowClickEvent<SelectionItem>) {
    emit("onClick", event.item);
    syncSelectedItems();
}

function onOpen(item: SelectionItem) {
    emit("onOpen", item);
}

function onSelectAll() {
    emit("onSelectAll");
    syncSelectedItems();
}

/** Format time stamp */
function formatTime(value: string) {
    if (value) {
        const date = new Date(value);
        return date.toLocaleString("default", {
            day: "numeric",
            month: "short",
            year: "numeric",
            minute: "numeric",
            hour: "numeric",
        });
    } else {
        return "-";
    }
}

function resetFilter() {
    filter.value = "";
}

function resetPagination(toInitialPage = 1) {
    currentPage.value = toInitialPage;
}

if (props.watchOnPageChanges) {
    watch(
        () => props.items,
        () => {
            if (props.itemsProvider === undefined) {
                resetPagination();
            }
        },
    );
}

const dialog = ref<InstanceType<typeof GModal> | null>(null);

watch(
    [
        () => props.itemsProvider,
        currentPage,
        perPage,
        filter,
        sortBy,
        sortDesc,
        () => props.providerUrl,
        () => props.optionsShow,
    ],
    () => {
        if (props.itemsProvider && props.optionsShow) {
            void loadProviderItems();
        }
    },
    { immediate: true },
);

watch(filter, () => {
    resetPagination();
});

watch(
    () => dialog.value,
    (newValue) => {
        if (newValue) {
            dialog.value?.showModal();
        }
    },
    { immediate: true },
);

watch(
    tableItems,
    () => {
        syncSelectedItems();
    },
    { immediate: true, deep: true },
);

defineExpose({
    resetFilter,
    resetPagination,
    currentPage,
});
</script>

<template>
    <GModal
        ref="dialog"
        class="selection-dialog-modal"
        size="medium"
        :show="props.modalShow"
        fixed-height
        footer
        @close="emit('onCancel')">
        <template v-slot:header>
            <div class="d-flex flex-column">
                <Heading v-if="props.title" size="sm"> {{ props.title }} </Heading>

                <FilterMenu
                    v-if="props.filterClass"
                    :name="props.title"
                    class="w-100"
                    :placeholder="props.searchTitle || props.title"
                    :filter-class="props.filterClass"
                    :filter-text.sync="filter"
                    :loading="props.isBusy"
                    :show-advanced.sync="showAdvancedSearch" />

                <DataDialogSearch
                    v-else
                    :value="filter"
                    :title="props.searchTitle || props.title"
                    @input="filter = $event" />
            </div>
        </template>
        <slot name="helper" />
        <BAlert v-if="errorMessage" variant="danger" show>
            {{ errorMessage }}
        </BAlert>
        <div v-else>
            <div v-if="optionsShow" data-description="selection dialog options">
                <GTable
                    class="selection-dialog-table"
                    clickable-rows
                    compact
                    hover
                    :current-page="currentPage"
                    :fields="fieldDetails"
                    :filter="filter"
                    :items="tableItems"
                    :loading="isBusy"
                    :local-filtering="!usingProvider"
                    :local-sorting="!usingProvider"
                    :per-page="perPage"
                    :selectable="props.selectable"
                    :selected-items="selectedItems"
                    :show-select-all="props.selectable"
                    @row-click="onRowClick"
                    @select-all="onSelectAll"
                    @sort-changed="onSortChanged">
                    <template v-slot:cell(label)="data">
                        <div style="cursor: pointer">
                            <pre
                                v-if="isEncoded"
                                :title="`label-${data.item.url}`"><code>{{ data.value ? data.value : "-" }}</code></pre>
                            <span v-else>
                                <div v-if="data.item.isLeaf">
                                    <i :class="leafIcon" />
                                    <span :title="`label-${data.item.url}`">{{ data.value ? data.value : "-" }}</span>
                                </div>
                                <div
                                    v-else
                                    role="button"
                                    tabindex="0"
                                    @click.stop="onOpen(data.item)"
                                    @keydown.enter.stop="onOpen(data.item)"
                                    @keydown.space.stop.prevent="onOpen(data.item)">
                                    <FontAwesomeIcon :icon="props.folderIcon" />
                                    <BLink :title="`label-${data.item.url}`">{{ data.value ? data.value : "-" }}</BLink>
                                </div>
                            </span>
                        </div>
                    </template>

                    <template v-slot:cell(details)="data">
                        <span :title="`details-${data.item.url}`">{{ data.value ? data.value : "-" }}</span>
                    </template>

                    <template v-slot:cell(tags)="data">
                        <StatelessTags v-if="data.value?.length > 0" :value="data.value" :disabled="true" />
                        <span v-else>-</span>
                    </template>

                    <template v-slot:cell(time)="data">
                        {{ formatTime(data.value) }}
                    </template>

                    <template v-slot:cell(update_time)="data">
                        {{ formatTime(data.value) }}
                    </template>
                </GTable>

                <div v-if="isBusy" class="text-center">
                    <BSpinner small type="grow" />
                    <BSpinner small type="grow" />
                    <BSpinner small type="grow" />
                </div>
                <div v-else-if="totalItems === 0">
                    <div v-if="filter">
                        No search results found for: <b> {{ filter }} </b>.
                    </div>
                    <div v-else>No entries.</div>
                </div>
            </div>
            <div v-else data-description="selection dialog spinner">
                <FontAwesomeIcon :icon="faSpinner" spin />
                <span>Please wait...</span>
            </div>
        </div>
        <template v-slot:footer>
            <div class="d-flex justify-content-between w-100">
                <div>
                    <BButton v-if="undoShow" data-description="selection dialog undo" size="sm" @click="emit('onUndo')">
                        <FontAwesomeIcon :icon="faCaretLeft" />
                        Back
                    </BButton>
                    <slot v-if="!errorMessage" name="buttons" />
                </div>
                <BPagination
                    v-if="totalItems > perPage"
                    v-model="currentPage"
                    class="justify-content-md-center m-0"
                    size="sm"
                    :per-page="perPage"
                    :total-rows="totalItems" />
                <div>
                    <BButton
                        data-description="selection dialog cancel"
                        size="sm"
                        variant="secondary"
                        @click="emit('onCancel')">
                        <FontAwesomeIcon :icon="faTimes" />
                        Cancel
                    </BButton>
                    <BButton
                        v-if="multiple || !fileMode"
                        data-description="selection dialog ok"
                        size="sm"
                        variant="primary"
                        :disabled="disableOk"
                        @click="emit('onOk')">
                        <FontAwesomeIcon :icon="faCheck" />
                        {{ okButtonText }}
                    </BButton>
                </div>
            </div>
        </template>
    </GModal>
</template>
