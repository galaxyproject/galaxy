<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faCaretLeft, faCheck, faFolder, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BPagination } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import type { ItemsProvider, SelectItemsProvider } from "@/components/SelectionDialog/selectionTypes";
import { type SelectItemsState, useSelectItems } from "@/composables/useSelectItems";
import type Filtering from "@/utils/filtering";

import type { SelectionItem } from "./selectionTypes";

import GButton from "../BaseComponents/GButton.vue";
import GModal from "../BaseComponents/GModal.vue";
import Heading from "../Common/Heading.vue";
import SelectionList from "@/components/SelectionDialog/SelectionList.vue";
import SelectionSearch from "@/components/SelectionDialog/SelectionSearch.vue";

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
    title?: string;
    searchTitle?: string;
    okButtonText?: string;
    filterClass?: Filtering<any>;
    watchOnPageChanges?: boolean;
    /** Data source; the dialog loads, pages, searches and navigates through it. */
    provider?: SelectItemsProvider;
    /** Caller-owned useSelectItems() state, for callers that read the path or selection themselves. */
    state?: SelectItemsState;
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
    title: "",
    searchTitle: undefined,
    okButtonText: "Select",
    filterClass: undefined,
    watchOnPageChanges: true,
    provider: undefined,
    state: undefined,
});

const emit = defineEmits<{
    (e: "onCancel"): void;
    (e: "onClick", record: SelectionItem): void;
    (e: "onOk"): void;
    (e: "onOpen", record: SelectionItem): void;
    (e: "onSelectAll", selected: boolean): void;
    (e: "onUndo"): void;
}>();

const filter = ref("");
const currentPage = ref(1);
const perPage = ref(25);

const providerRequestId = ref(0);
const providerItems = ref<SelectionItem[]>([]);
const sortBy = ref<string | undefined>(undefined);
const sortDesc = ref<boolean | undefined>(undefined);

const usingProvider = computed(() => Boolean(props.itemsProvider));

const selection = props.state ?? (props.provider ? useSelectItems(() => props.provider!) : undefined);

const listItems = computed(() => (selection ? selection.items.value : tableItems.value));
const listTotal = computed(() => (selection ? selection.total.value : props.totalItems));
const listPerPage = computed(() => (selection ? selection.perPage.value : perPage.value));
const listBusy = computed(() => props.isBusy || Boolean(selection?.loading.value));
const listError = computed(() => props.errorMessage || selection?.error.value || "");
const listReady = computed(() => (selection ? selection.loaded.value : props.optionsShow));
const listUndo = computed(() => props.undoShow || Boolean(selection?.path.value.length));
// the state owns the sort and changes it per level, so the header follows it ("" = unsorted)
const listSortBy = computed(() => (selection ? (selection.sortBy.value ?? "") : undefined));
const listSortDesc = computed(() => selection?.sortDesc.value);
const listFilter = computed({
    get: () => (selection ? selection.filter.value : filter.value),
    set: (value: string) => {
        if (selection) {
            selection.filter.value = value;
        } else {
            filter.value = value;
        }
    },
});
const listPage = computed({
    get: () => (selection ? selection.page.value : currentPage.value),
    set: (value: number) => {
        if (selection) {
            selection.page.value = value;
        } else {
            currentPage.value = value;
        }
    },
});

const okButtonText = computed(() => {
    return props.okButtonText ? props.okButtonText : props.fileMode ? "Select" : "Select this folder";
});

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
    if (selection) {
        const formatter = props.fields.find((field) => field.key === newSortBy)?.formatter;
        selection.setSort(newSortBy, newSortDesc, formatter);
    } else {
        sortBy.value = newSortBy || undefined;
        sortDesc.value = newSortDesc;
    }
}

function onClick(item: SelectionItem) {
    if (selection && props.selectable) {
        selection.toggle(item);
    }
    emit("onClick", item);
}

function onOpen(item: SelectionItem) {
    selection?.open(item);
    emit("onOpen", item);
}

function onSelectAll(selected: boolean) {
    selection?.selectAll(selected);
    emit("onSelectAll", selected);
}

function onUndo() {
    selection?.back();
    emit("onUndo");
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

                <SelectionSearch
                    v-model:filter="listFilter"
                    :filter-class="props.filterClass"
                    :loading="listBusy"
                    :name="props.title"
                    :placeholder="props.searchTitle || props.title" />
            </div>
        </template>
        <slot name="helper" />
        <SelectionList
            :current-page="listPage"
            :error-message="listError"
            :fields="props.fields"
            :filter="listFilter"
            :folder-icon="props.folderIcon"
            :is-busy="listBusy"
            :is-encoded="isEncoded"
            :items="listItems"
            :leaf-icon="leafIcon"
            :local-paging="!selection && !usingProvider"
            :options-show="listReady"
            :per-page="listPerPage"
            :selectable="props.selectable"
            :sort-by="listSortBy"
            :sort-desc="listSortDesc"
            :total-items="listTotal"
            @click="onClick"
            @open="onOpen"
            @select-all="onSelectAll"
            @sort-changed="onSortChanged" />
        <template v-slot:footer>
            <div class="d-flex justify-content-between w-100">
                <div>
                    <GButton v-if="listUndo" data-description="selection dialog undo" size="small" @click="onUndo">
                        <FontAwesomeIcon :icon="faCaretLeft" />
                        Back
                    </GButton>
                    <slot v-if="!listError" name="buttons" />
                </div>
                <BPagination
                    v-if="listTotal > listPerPage"
                    v-model="listPage"
                    class="justify-content-md-center m-0"
                    size="sm"
                    :per-page="listPerPage"
                    :total-rows="listTotal" />
                <div>
                    <GButton data-description="selection dialog cancel" size="small" @click="emit('onCancel')">
                        <FontAwesomeIcon :icon="faTimes" />
                        Cancel
                    </GButton>
                    <GButton
                        v-if="multiple || !fileMode"
                        data-description="selection dialog ok"
                        size="small"
                        color="blue"
                        :disabled="disableOk"
                        @click="emit('onOk')">
                        <FontAwesomeIcon :icon="faCheck" />
                        {{ okButtonText }}
                    </GButton>
                </div>
            </div>
        </template>
    </GModal>
</template>
