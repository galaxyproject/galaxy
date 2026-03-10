<script setup lang="ts">
import { BButton, BFormCheckbox, BModal, BPagination } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import localize from "@/utils/localization";
import { bytesToString } from "@/utils/utils";

import { type CleanableItem, type CleanupOperation, PaginationOptions, type SortableKey } from "./model";

import GTable from "@/components/Common/GTable.vue";
import UtcDate from "@/components/UtcDate.vue";

interface ReviewCleanupDialogProps {
    operation?: CleanupOperation;
    totalItems?: number;
    modalStatic?: boolean;
}

const props = withDefaults(defineProps<ReviewCleanupDialogProps>(), {
    operation: undefined,
    totalItems: 0,
});

const emit = defineEmits<{
    (event: "onConfirmCleanupSelectedItems", items: CleanableItem[]): void;
}>();

const permanentlyDeleteText = localize("Permanently delete");
const captionText = localize("To free up account space, review and select items to be permanently deleted here.");
const agreementText = localize("I understand that once I delete the items, they cannot be recovered.");
const fields: TableField[] = [
    {
        key: "selected",
        label: "",
        sortable: false,
    },
    {
        key: "name",
        label: localize("Name"),
        sortable: true,
    },
    {
        key: "size",
        label: localize("Size"),
        sortable: true,
        formatter: toNiceSize,
    },
    {
        key: "update_time",
        label: localize("Updated"),
        sortable: true,
    },
];

const MAXIMUM_ITEMS_PER_PAGE = 25;

const sortBy = ref<SortableKey>("size");
const sortDesc = ref(true);
const currentPage = ref(1);
const totalRows = ref(1);
const allSelected = ref(false);
const indeterminate = ref(false);
const showDialog = ref(false);
const items = ref<CleanableItem[]>([]);
const selectedItems = ref<CleanableItem[]>([]);
const confirmChecked = ref(false);
const isBusy = ref(false);

const selectedItemCount = computed(() => {
    return selectedItems.value.length;
});

const hasItemsSelected = computed(() => {
    return selectedItemCount.value > 0;
});

const hasPages = computed(() => {
    return totalRows.value > MAXIMUM_ITEMS_PER_PAGE;
});

const title = computed(() => {
    return props.operation?.name ?? "";
});

const confirmationTitle = computed(() => {
    return `Permanently delete ${selectedItemCount.value} items?`;
});

const deleteButtonVariant = computed(() => {
    return hasItemsSelected.value ? "danger" : "";
});

const deleteItemsText = computed(() => {
    return hasItemsSelected.value ? `${selectedItemCount.value} items` : "";
});

const confirmButtonVariant = computed(() => {
    return confirmChecked.value ? "danger" : "";
});

async function loadItems() {
    if (!props.operation) {
        items.value = [];
        return;
    }

    try {
        isBusy.value = true;
        const page = currentPage.value > 0 ? currentPage.value - 1 : 0;
        const offset = page * MAXIMUM_ITEMS_PER_PAGE;
        const options = new PaginationOptions({
            offset: offset,
            limit: MAXIMUM_ITEMS_PER_PAGE,
            sortBy: sortBy.value,
            sortDesc: sortDesc.value,
        });
        const result = await props.operation.fetchItems(options);
        items.value = result;
    } finally {
        isBusy.value = false;
    }
}

function toNiceSize(sizeInBytes: number) {
    return bytesToString(sizeInBytes, true, undefined);
}

async function toggleSelectAll(checked: boolean) {
    if (checked) {
        await selectAllItems();
    } else {
        unselectAllItems();
    }
}

function openModal() {
    showDialog.value = true;
}

function hideModal() {
    showDialog.value = false;
}

function onShowModal() {
    resetModal();
    loadItems();
}

function resetModal() {
    unselectAllItems();
}

function resetConfirmationModal() {
    confirmChecked.value = false;
}

function onConfirmCleanupSelectedItems() {
    emit("onConfirmCleanupSelectedItems", selectedItems.value);
    hideModal();
}

function onSort(sortByKey: string, sortDescending: boolean) {
    sortBy.value = sortByKey as SortableKey;
    sortDesc.value = sortDescending;
}

function isItemSelected(item: CleanableItem): boolean {
    return selectedItems.value.some((selectedItem) => selectedItem.id === item.id);
}

function toggleItemSelection(item: CleanableItem): void {
    const index = selectedItems.value.findIndex((selectedItem) => selectedItem.id === item.id);
    if (index === -1) {
        selectedItems.value = [...selectedItems.value, item];
    } else {
        selectedItems.value = selectedItems.value.filter((selectedItem) => selectedItem.id !== item.id);
    }
}

async function selectAllItems() {
    isBusy.value = true;
    const operation = props.operation;
    if (!operation) {
        return;
    }
    const allItems = await operation.fetchItems(
        new PaginationOptions({
            offset: 0,
            limit: totalRows.value,
            sortBy: sortBy.value,
            sortDesc: sortDesc.value,
        }),
    );
    items.value = allItems;
    selectedItems.value = allItems;
    isBusy.value = false;
}

function unselectAllItems() {
    selectedItems.value = [];
}

watch(
    () => props.totalItems,
    (newVal) => {
        currentPage.value = 1;
        totalRows.value = newVal;
    },
);

watch(
    () => props.operation,
    () => {
        currentPage.value = 1;
    },
);

watch([currentPage, sortBy, sortDesc], async () => {
    await loadItems();
});

watch(selectedItems, (newVal) => {
    if (newVal.length === 0) {
        indeterminate.value = false;
        allSelected.value = false;
    } else if (newVal.length === totalRows.value) {
        indeterminate.value = false;
        allSelected.value = true;
    } else {
        indeterminate.value = true;
        allSelected.value = false;
    }
});

defineExpose({
    openModal,
    selectedItems,
});
</script>

<template>
    <BModal v-model="showDialog" title-tag="h2" :static="modalStatic" centered @show="onShowModal">
        <template v-slot:modal-title>
            {{ title }}
            <span class="text-primary h3">{{ totalRows }} items</span>
        </template>
        <div>
            {{ captionText }}
        </div>

        <GTable
            v-if="operation"
            hover
            :fields="fields"
            :items="items"
            :sort-by="sortBy"
            :sort-desc="sortDesc"
            :loading="isBusy"
            :local-filtering="false"
            :local-sorting="false"
            sticky-header="50vh"
            data-test-id="review-table"
            @sort-changed="onSort">
            <template v-slot:head(selected)>
                <BFormCheckbox
                    v-model="allSelected"
                    :indeterminate="indeterminate"
                    data-test-id="select-all-checkbox"
                    @change="toggleSelectAll" />
            </template>

            <template v-slot:cell(selected)="data">
                <BFormCheckbox
                    :key="data.index"
                    :checked="isItemSelected(data.item)"
                    @change="toggleItemSelection(data.item)" />
            </template>

            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
        </GTable>

        <template v-slot:modal-footer>
            <BPagination
                v-if="hasPages"
                v-model="currentPage"
                :total-rows="totalRows"
                :per-page="MAXIMUM_ITEMS_PER_PAGE" />

            <BButton
                v-b-modal.confirmation-modal
                :disabled="!hasItemsSelected"
                :variant="deleteButtonVariant"
                class="mx-2"
                data-test-id="delete-button">
                {{ permanentlyDeleteText }} {{ deleteItemsText }}
            </BButton>
        </template>

        <BModal
            id="confirmation-modal"
            :title="confirmationTitle"
            title-tag="h2"
            :ok-title="permanentlyDeleteText"
            :ok-variant="confirmButtonVariant"
            :ok-disabled="!confirmChecked"
            static
            centered
            @show="resetConfirmationModal"
            @ok="onConfirmCleanupSelectedItems">
            <BFormCheckbox id="confirm-delete-checkbox" v-model="confirmChecked" data-test-id="agreement-checkbox">
                {{ agreementText }}
            </BFormCheckbox>
        </BModal>
    </BModal>
</template>
