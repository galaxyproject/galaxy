<script setup lang="ts">
import { type IconDefinition, library } from "@fortawesome/fontawesome-svg-core";
import { faCheckSquare, faMinusSquare, faSquare } from "@fortawesome/free-regular-svg-icons";
import { faCaretLeft, faCheck, faFolder, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BLink, BModal, BPagination, BSpinner, BTable } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { type ItemsProvider, SELECTION_STATES, type SelectionState } from "@/components/SelectionDialog/selectionTypes";
import type Filtering from "@/utils/filtering";

import type { FieldEntry, SelectionItem } from "./selectionTypes";

import FilterMenu from "@/components/Common/FilterMenu.vue";
import Heading from "@/components/Common/Heading.vue";
import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

library.add(faCaretLeft, faCheck, faCheckSquare, faFolder, faMinusSquare, faSpinner, faSquare, faTimes);

const LABEL_FIELD: FieldEntry = { key: "label", sortable: true };
const SELECT_ICON_FIELD: FieldEntry = { key: "__select_icon__", label: "", sortable: false };

interface Props {
    disableOk?: boolean;
    errorMessage?: string;
    fileMode?: boolean;
    fields?: FieldEntry[];
    isBusy?: boolean;
    isEncoded?: boolean;
    items?: SelectionItem[];
    itemsProvider?: ItemsProvider;
    providerUrl?: string;
    totalItems?: number;
    leafIcon?: string;
    folderIcon?: IconDefinition;
    modalShow?: boolean;
    modalStatic?: boolean;
    multiple?: boolean;
    optionsShow?: boolean;
    undoShow?: boolean;
    selectAllVariant?: SelectionState;
    showSelectIcon?: boolean;
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
    modalStatic: false,
    multiple: false,
    optionsShow: false,
    undoShow: false,
    selectAllVariant: SELECTION_STATES.UNSELECTED,
    showSelectIcon: false,
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

const okButtonText = computed(() => {
    return props.okButtonText ? props.okButtonText : props.fileMode ? "Select" : "Select this folder";
});

const fieldDetails = computed(() => {
    const fields = props.fields.slice().map((x) => {
        x.sortable = x.sortable === undefined ? true : x.sortable;
        return x;
    });
    if (fields.length === 0) {
        fields.unshift(LABEL_FIELD);
    }
    if (props.showSelectIcon) {
        fields.unshift(SELECT_ICON_FIELD);
    }
    return fields;
});

function selectionIcon(variant: string) {
    switch (variant) {
        case SELECTION_STATES.SELECTED:
            return faCheckSquare;
        case SELECTION_STATES.MIXED:
            return faMinusSquare;
        default:
            return faSquare;
    }
}

/** Resets pagination when a filter/search word is entered **/
function filtered(items: SelectionItem[]) {
    if (props.itemsProvider === undefined) {
        resetPagination();
    }
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
        }
    );
}

defineExpose({
    resetFilter,
    resetPagination,
    currentPage,
});
</script>

<template>
    <BModal
        v-if="modalShow"
        modal-class="selection-dialog-modal"
        header-class="flex-column"
        visible
        :static="modalStatic"
        :title="title"
        @hide="emit('onCancel')">
        <template v-slot:modal-header>
            <slot name="header">
                <Heading v-if="props.title" h2> {{ props.title }} </Heading>

                <FilterMenu
                    v-if="props.filterClass"
                    :name="props.title"
                    class="w-100"
                    :placeholder="props.searchTitle || props.title"
                    :filter-class="props.filterClass"
                    :filter-text.sync="filter"
                    :loading="props.isBusy"
                    :show-advanced.sync="showAdvancedSearch" />

                <DataDialogSearch v-else v-model="filter" :title="props.searchTitle || props.title" />
            </slot>
        </template>
        <slot name="helper" />
        <BAlert v-if="errorMessage" variant="danger" show>
            {{ errorMessage }}
        </BAlert>
        <div v-else>
            <div v-if="optionsShow">
                <BTable
                    small
                    hover
                    class="selection-dialog-table"
                    primary-key="id"
                    :busy="isBusy"
                    :current-page="currentPage"
                    :items="itemsProvider ?? items"
                    :fields="fieldDetails"
                    :filter="filter"
                    :per-page="perPage"
                    @filtered="filtered"
                    @row-clicked="emit('onClick', $event)">
                    <template v-slot:head(__select_icon__)="">
                        <FontAwesomeIcon
                            class="select-checkbox cursor-pointer"
                            title="Check to select all datasets"
                            :icon="selectionIcon(selectAllVariant)"
                            @click="$emit('onSelectAll')" />
                    </template>
                    <template v-slot:cell(__select_icon__)="data">
                        <FontAwesomeIcon :icon="selectionIcon(data.item._rowVariant)" />
                    </template>
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
                                <div v-else @click.stop="emit('onOpen', data.item)">
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
                </BTable>
                <div v-if="isBusy" class="text-center">
                    <BSpinner small type="grow" />
                    <BSpinner small type="grow" />
                    <BSpinner small type="grow" />
                </div>
                <div v-else-if="totalItems === 0">
                    <div v-if="filter">
                        No search results found for: <b>{{ filter }}</b
                        >.
                    </div>
                    <div v-else>No entries.</div>
                </div>
            </div>
            <div v-else data-description="selection dialog spinner">
                <FontAwesomeIcon :icon="faSpinner" spin />
                <span>Please wait...</span>
            </div>
        </div>
        <template v-slot:modal-footer>
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
    </BModal>
</template>

<style>
.selection-dialog-modal .modal-body {
    max-height: 50vh;
    height: 50vh;
    overflow-y: auto;
}
</style>
