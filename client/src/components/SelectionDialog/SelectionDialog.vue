<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faCaretLeft, faCheck, faFolder, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BPagination } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import type { ItemsProvider } from "@/components/SelectionDialog/selectionTypes";
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
    sortBy.value = newSortBy || undefined;
    sortDesc.value = newSortDesc;
}

function onClick(item: SelectionItem) {
    emit("onClick", item);
}

function onOpen(item: SelectionItem) {
    emit("onOpen", item);
}

function onSelectAll(selected: boolean) {
    emit("onSelectAll", selected);
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
                    v-model:filter="filter"
                    :filter-class="props.filterClass"
                    :loading="props.isBusy"
                    :name="props.title"
                    :placeholder="props.searchTitle || props.title" />
            </div>
        </template>
        <slot name="helper" />
        <SelectionList
            :current-page="currentPage"
            :error-message="errorMessage"
            :fields="props.fields"
            :filter="filter"
            :folder-icon="props.folderIcon"
            :is-busy="isBusy"
            :is-encoded="isEncoded"
            :items="tableItems"
            :leaf-icon="leafIcon"
            :local-paging="!usingProvider"
            :options-show="optionsShow"
            :per-page="perPage"
            :selectable="props.selectable"
            :total-items="totalItems"
            @click="onClick"
            @open="onOpen"
            @select-all="onSelectAll"
            @sort-changed="onSortChanged" />
        <template v-slot:footer>
            <div class="d-flex justify-content-between w-100">
                <div>
                    <GButton
                        v-if="undoShow"
                        data-description="selection dialog undo"
                        size="small"
                        @click="emit('onUndo')">
                        <FontAwesomeIcon :icon="faCaretLeft" />
                        Back
                    </GButton>
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
