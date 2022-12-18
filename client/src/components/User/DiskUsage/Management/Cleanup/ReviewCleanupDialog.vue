<script setup lang="ts">
import localize from "@/utils/localization";
import { bytesToString } from "@/utils/utils";
import { BModal, BTable, BFormCheckbox, BLink, BPagination, BButton } from "bootstrap-vue";
import UtcDate from "@/components/UtcDate.vue";
import type { CleanableItem, CleanupOperation } from "./model";
import { computed, ref, watch } from "vue";

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
const captionText = localize("To free up account space, review and select items to be permanently deleted or");
const agreementText = localize("I understand that once I delete the items, they cannot be recovered.");
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
        label: "Updated",
        key: "update_time",
        sortable: true,
    },
];

type SortableKey = "name" | "size" | "update_time";

const sortBy = ref(<SortableKey>"size");
const sortDesc = ref(true);
const perPage = ref(50);
const currentPage = ref(1);
const totalRows = ref(1);
const allSelected = ref(false);
const indeterminate = ref(false);
const showDialog = ref(false);
const items = ref<CleanableItem[]>([]);
const selectedItems = ref<CleanableItem[]>([]);
const itemLimit = ref(500);
const confirmChecked = ref(false);
const isBusy = ref(false);

const selectedItemCount = computed(() => {
    return selectedItems.value.length;
});

const hasItemsSelected = computed(() => {
    return selectedItemCount.value > 0;
});

const hasPages = computed(() => {
    return totalRows.value > perPage.value;
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

const rowLimitReached = computed(() => {
    return totalRows.value >= itemLimit.value;
});

const rowLimitReachedText = computed(() => {
    return localize(
        `Displaying a maximum of ${itemLimit.value} items here. If there are more, you can rerun this operation after deleting some.`
    );
});

watch(props, (newVal) => {
    currentPage.value = 1;
    totalRows.value = newVal.totalItems;
});

watch(selectedItems, (newVal) => {
    if (newVal.length === 0) {
        indeterminate.value = false;
        allSelected.value = false;
    } else if (newVal.length === items.value.length) {
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

function toggleSelectAll(checked: boolean) {
    selectedItems.value = checked ? items.value : [];
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
    selectedItems.value = [];
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
        const options = {
            offset: offset,
            limit: ctx.perPage,
            sortBy: sortBy.value,
            sortDesc: sortDesc.value,
        };
        const result = await props.operation.fetchItems(options);
        return result;
    } catch (error) {
        return [];
    }
}

async function onSelectAllItems() {
    isBusy.value = true;
    const allItems = await props.operation.fetchItems({
        offset: 0,
        limit: totalRows.value,
        sortBy: sortBy.value,
        sortDesc: sortDesc.value,
    });
    selectedItems.value = allItems;
    isBusy.value = false;
}

defineExpose({
    openModal,
    selectedItems,
});
</script>

<template>
    <b-modal v-model="showDialog" title-tag="h2" :static="modalStatic" centered @show="onShowModal">
        <template v-slot:modal-title>
            {{ title }}
            <span class="text-primary h3">{{ totalItems }}<span v-if="rowLimitReached">+</span> items</span>
        </template>
        <div>
            {{ captionText }}
            <b>
                <b-link @click="onSelectAllItems">select all {{ totalItems }} items</b-link>
            </b>
        </div>
        <b-table
            v-if="operation"
            v-model="items"
            :fields="fields"
            :items="itemsProvider"
            :per-page="perPage"
            :current-page="currentPage"
            :busy="isBusy"
            hover
            no-local-sorting
            no-provider-filtering
            sticky-header="50vh"
            data-test-id="review-table"
            @sort-changed="onSort">
            <template v-slot:head(selected)>
                <b-form-checkbox
                    v-model="allSelected"
                    :indeterminate="indeterminate"
                    data-test-id="select-all-checkbox"
                    @change="toggleSelectAll" />
            </template>
            <template v-slot:cell(selected)="data">
                <b-form-checkbox :key="data.index" v-model="selectedItems" :checked="allSelected" :value="data.item" />
            </template>
            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
        </b-table>
        <template v-slot:modal-footer>
            <span v-if="rowLimitReached" class="font-italic">{{ rowLimitReachedText }}</span>
            <b-pagination v-if="hasPages" v-model="currentPage" :total-rows="totalRows" :per-page="perPage" />
            <b-button
                v-b-modal.confirmation-modal
                :disabled="!hasItemsSelected"
                :variant="deleteButtonVariant"
                class="mx-2"
                data-test-id="delete-button">
                {{ permanentlyDeleteText }} {{ deleteItemsText }}
            </b-button>
        </template>

        <b-modal
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
            <b-form-checkbox id="confirm-delete-checkbox" v-model="confirmChecked" data-test-id="agreement-checkbox">
                {{ agreementText }}
            </b-form-checkbox>
        </b-modal>
    </b-modal>
</template>
