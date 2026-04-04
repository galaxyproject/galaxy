<script setup lang="ts">
import { BFormCheckbox, BPagination } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import localize from "@/utils/localization";
import { bytesToString } from "@/utils/utils";

import { type CleanableItem, type CleanupOperation, PaginationOptions, type SortableKey } from "./model";

import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import GTable from "@/components/Common/GTable.vue";
import Heading from "@/components/Common/Heading.vue";
import UtcDate from "@/components/UtcDate.vue";

interface ReviewCleanupDialogProps {
    operation?: CleanupOperation;
    totalItems?: number;
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
const openConfirmationModal = ref(false);

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
    return `Permanently delete ${selectedItemCount.value} item${selectedItemCount.value > 1 ? "s" : ""}?`;
});

const deleteItemsText = computed(() => {
    return hasItemsSelected.value ? `${selectedItemCount.value} item${selectedItemCount.value > 1 ? "s" : ""}` : "";
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

async function onShowModal() {
    resetModal();
    await loadItems();
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

watch(showDialog, (newVal) => {
    if (newVal) {
        onShowModal();
    }
});

watch(openConfirmationModal, (newVal) => {
    if (newVal) {
        resetConfirmationModal();
    }
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
    <GModal footer :show.sync="showDialog" size="medium">
        <template v-slot:header>
            <Heading class="w-100 d-flex justify-content-between mb-0" size="md">
                <div>{{ title }}</div>
                <div class="text-primary">{{ totalRows }} {{ totalRows === 1 ? "item" : "items" }}</div>
            </Heading>
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

        <template v-slot:footer>
            <div
                class="d-flex align-items-center"
                :class="hasPages ? 'justify-content-between' : 'justify-content-end'">
                <BPagination
                    v-if="hasPages"
                    v-model="currentPage"
                    class="mb-0"
                    :total-rows="totalRows"
                    :per-page="MAXIMUM_ITEMS_PER_PAGE" />

                <GButton
                    :disabled="!hasItemsSelected"
                    color="red"
                    class="mx-2"
                    data-test-id="delete-button"
                    @click="openConfirmationModal = true">
                    {{ permanentlyDeleteText }} {{ deleteItemsText }}
                </GButton>
            </div>
        </template>

        <GModal
            id="confirmation-modal"
            confirm
            :show.sync="openConfirmationModal"
            :title="confirmationTitle"
            :ok-text="permanentlyDeleteText"
            ok-color="red"
            :ok-disabled="!confirmChecked"
            @ok="onConfirmCleanupSelectedItems">
            <BFormCheckbox id="confirm-delete-checkbox" v-model="confirmChecked" data-test-id="agreement-checkbox">
                {{ agreementText }}
            </BFormCheckbox>
        </GModal>
    </GModal>
</template>
