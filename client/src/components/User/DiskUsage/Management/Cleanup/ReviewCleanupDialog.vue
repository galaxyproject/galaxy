<script setup lang="ts">
import { BButton, BFormCheckbox, BModal, BPagination, BTable } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import localize from "@/utils/localization";
import { bytesToString } from "@/utils/utils";

import { type CleanableItem, type CleanupOperation, PaginationOptions, type SortableKey } from "./model";

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

const permanentlyDeleteText = localize("永久删除");
const captionText = localize("要释放账户空间，请在此处审查并选择要永久删除的项目。");
const agreementText = localize("我了解一旦删除这些项目，它们将无法恢复。");
const fields = [
    {
        key: "selected",
        label: "",
        sortable: false,
    },
    {
        key: "name",
        sortable: true,
    },
    {
        key: "size",
        sortable: true,
        formatter: toNiceSize,
    },
    {
        label: "更新时间",
        key: "update_time",
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
    return `永久删除 ${selectedItemCount.value} 个项目？`;
});

const deleteButtonVariant = computed(() => {
    return hasItemsSelected.value ? "danger" : "";
});

const deleteItemsText = computed(() => {
    return hasItemsSelected.value ? `${selectedItemCount.value} 个项目` : "";
});

const confirmButtonVariant = computed(() => {
    return confirmChecked.value ? "danger" : "";
});

watch(props, (newVal) => {
    currentPage.value = 1;
    totalRows.value = newVal.totalItems;
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

function onSort(props: { sortBy: SortableKey; sortDesc: boolean }) {
    sortBy.value = props.sortBy;
    sortDesc.value = props.sortDesc;
}

async function itemsProvider(ctx: { currentPage: number; perPage: number }) {
    try {
        const page = ctx.currentPage > 0 ? ctx.currentPage - 1 : 0;
        const offset = page * ctx.perPage;
        const options = new PaginationOptions({
            offset: offset,
            limit: ctx.perPage,
            sortBy: sortBy.value,
            sortDesc: sortDesc.value,
        });
        const result = await props.operation.fetchItems(options);
        return result;
    } catch (error) {
        return [];
    }
}

async function selectAllItems() {
    isBusy.value = true;
    const allItems = await props.operation.fetchItems(
        new PaginationOptions({
            offset: 0,
            limit: totalRows.value,
            sortBy: sortBy.value,
            sortDesc: sortDesc.value,
        })
    );
    items.value = allItems;
    selectedItems.value = allItems;
    isBusy.value = false;
}

function unselectAllItems() {
    selectedItems.value = [];
}

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
        <BTable
            v-if="operation"
            v-model="items"
            :fields="fields"
            :items="itemsProvider"
            :per-page="MAXIMUM_ITEMS_PER_PAGE"
            :current-page="currentPage"
            :busy="isBusy"
            hover
            no-sort-reset
            no-local-sorting
            no-provider-filtering
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
                <BFormCheckbox :key="data.index" v-model="selectedItems" :checked="allSelected" :value="data.item" />
            </template>
            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
        </BTable>
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
