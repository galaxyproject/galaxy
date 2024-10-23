<script setup lang="ts">
import { type IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faCaretLeft, faCheck, faFile, faFolder, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BModal, BOverlay, BPagination } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { defaultSortKeys, type SortKey } from "@/components/Common";
import {
    type ItemsProvider,
    type ItemsProviderContext,
    SELECTION_STATES,
    type SelectionItem,
    type SelectionState,
} from "@/components/SelectionDialog/selectionTypes";
import type Filtering from "@/utils/filtering";

import FilterMenu from "@/components/Common/FilterMenu.vue";
import Heading from "@/components/Common/Heading.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";
import SelectionCard from "@/components/SelectionDialog/SelectionCard.vue";

interface Props {
    disableOk?: boolean;
    errorMessage?: string;
    fileMode?: boolean;
    sortKeys?: SortKey[];
    isBusy?: boolean;
    isEncoded?: boolean;
    items?: SelectionItem[];
    itemsProvider?: ItemsProvider;
    providerUrl?: string;
    totalItems?: number;
    leafIcon?: IconDefinition;
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
    filterClass?: Filtering<unknown>;
}

const props = withDefaults(defineProps<Props>(), {
    disableOk: false,
    errorMessage: "",
    fileMode: true,
    sortKeys: () => defaultSortKeys,
    isBusy: false,
    isEncoded: false,
    items: () => [],
    itemsProvider: undefined,
    providerUrl: undefined,
    totalItems: 0,
    leafIcon: () => faFile,
    folderIcon: () => faFolder,
    modalShow: true,
    modalStatic: false,
    multiple: false,
    optionsShow: false,
    undoShow: false,
    selectAllVariant: SELECTION_STATES.UNSELECTED,
    showSelectIcon: false,
    title: undefined,
    searchTitle: undefined,
    okButtonText: "Select",
    filterClass: undefined,
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
const listHeader = ref<any | null>(null);
const currentPage = ref(1);
const perPage = ref(25);
const showAdvancedSearch = ref(false);
const filteredItems = ref<SelectionItem[]>(props.items);
const sortDesc = computed(() => (listHeader.value && listHeader.value.sortDesc) ?? true);
const sortBy = computed(() => (listHeader.value && listHeader.value.sortBy) || "update_time");
const allSelected = computed(() => props.selectAllVariant === SELECTION_STATES.SELECTED);
const intermediateSelected = computed(() => props.selectAllVariant === SELECTION_STATES.MIXED);
const okButtonText = computed(() => {
    return props.okButtonText ? props.okButtonText : props.fileMode ? "Select" : "Select this folder";
});

function resetFilter() {
    filter.value = "";
}

function resetPagination() {
    currentPage.value = 1;
}

async function fetchItems() {
    if (props.itemsProvider) {
        const context: ItemsProviderContext = {
            currentPage: currentPage.value,
            perPage: perPage.value,
            filter: filter.value,
            sortBy: sortBy.value,
            sortDesc: sortDesc.value,
        };

        filteredItems.value = await props.itemsProvider(context);
    }
}

watch(
    () => props.items,
    () => {
        filteredItems.value = props.items.slice(
            (currentPage.value - 1) * perPage.value,
            currentPage.value * perPage.value
        );
    }
);

watch(
    () => [props.itemsProvider, currentPage.value, perPage.value, filter.value, sortBy.value, sortDesc.value],
    () => {
        if (props.itemsProvider !== undefined) {
            fetchItems();
        }
    }
);
watch(
    () => props.providerUrl,
    () => {
        // We need to reset the current page when drilling down sub-folders
        if (props.itemsProvider !== undefined) {
            resetPagination();
        }
    }
);

defineExpose({
    resetFilter,
    resetPagination,
});
</script>

<template>
    <BModal
        v-if="modalShow"
        size="xl"
        centered
        modal-class="selection-dialog-modal"
        header-class="selection-dialog-header"
        visible
        :no-close-on-esc="!disableOk"
        :no-close-on-backdrop="!disableOk"
        :static="modalStatic"
        :title="title"
        @hide="emit('onCancel')">
        <template v-slot:modal-header>
            <div id="selection-dialog-header" class="selection-dialog-header">
                <slot name="header">
                    <Heading v-if="props.title" h2>
                        {{ props.title }}
                    </Heading>

                    <FilterMenu
                        v-if="props.filterClass"
                        :name="props.title"
                        class="w-100 mb-2"
                        :placeholder="props.searchTitle || props.title"
                        :filter-class="props.filterClass"
                        :filter-text.sync="filter"
                        :loading="props.isBusy"
                        :show-advanced.sync="showAdvancedSearch" />

                    <DataDialogSearch
                        v-else
                        v-model="filter"
                        class="w-100 mb-2"
                        :title="props.searchTitle || props.title" />

                    <div class="selection-dialog-filter-selection">
                        <ListHeader
                            ref="listHeader"
                            :intermediate-selected="intermediateSelected"
                            :all-selected="allSelected"
                            :show-select-all="props.showSelectIcon && props.multiple"
                            @select-all="emit('onSelectAll')" />
                    </div>
                </slot>
            </div>
        </template>

        <slot name="helper" />

        <div v-if="optionsShow">
            <BAlert v-if="errorMessage" variant="danger" show>
                {{ errorMessage }}
            </BAlert>

            <div v-if="totalItems === 0">
                <BAlert v-if="filter" variant="info" show>
                    No search results found for:
                    <b>{{ filter }}</b
                    >.
                </BAlert>

                <BAlert v-else variant="info" show> No entries. </BAlert>
            </div>

            <BOverlay :show="!optionsShow || isBusy">
                <div v-for="item in filteredItems" :key="item.id">
                    <SelectionCard
                        :id="`selection-card-item-${item.id}`"
                        :show-select-icon="props.showSelectIcon"
                        :item="item"
                        :is-encoded="props.isEncoded"
                        @select="emit('onClick', $event)"
                        @open="emit('onOpen', $event)" />
                </div>
            </BOverlay>
        </div>

        <template v-slot:modal-footer>
            <div class="d-flex justify-content-between w-100">
                <div>
                    <BButton
                        v-if="undoShow"
                        data-description="selection dialog undo"
                        variant="outline-primary"
                        size="sm"
                        @click="emit('onUndo')">
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
                        variant="outline-danger"
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

<style lang="scss">
@import "breakpoints.scss";

.selection-dialog-modal {
    .modal-dialog {
        width: inherit;
        max-width: $breakpoint-xl;

        .modal-body {
            max-height: 70vh;
            min-height: 70vh;
            overflow-y: auto;
        }
    }
}

.selection-dialog-header {
    position: sticky;
    flex-direction: column;
    padding-bottom: 0 !important;
    width: 100%;
}
</style>

<style scoped lang="scss">
@import "theme/blue.scss";

.selection-dialog-filter-selection {
    display: flex;
    margin-bottom: 0.25rem;
    align-items: center;
    justify-content: space-between;
}
</style>
