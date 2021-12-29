<template>
    <div>
        <b-modal ref="purgeable-details-modal" id="purgeable-details-modal" :title="title" centered @show="resetModal">
            <b-table
                id="purgeable-items-table"
                hover
                caption-top
                :fields="fields"
                :items="items"
                :per-page="perPage"
                :current-page="currentPage"
                sticky-header="50vh">
                <template v-slot:table-caption>
                    To free up account space, select items to be permanently deleted.
                </template>
                <template v-slot:head(selected)>
                    <b-form-checkbox
                        v-model="allSelected"
                        :indeterminate="indeterminate"
                        @change="toggleSelectAll"></b-form-checkbox>
                </template>
                <template v-slot:cell(selected)="data">
                    <b-form-checkbox
                        v-model="selectedItems"
                        :checked="allSelected"
                        :key="data.index"
                        :value="data.item"></b-form-checkbox>
                </template>
                <template v-slot:cell(update_time)="data">
                    <UtcDate :date="data.value" mode="elapsed" />
                </template>
            </b-table>
            <template v-slot:modal-footer>
                <b-pagination
                    v-if="hasPages"
                    v-model="currentPage"
                    :total-rows="totalRows"
                    :per-page="perPage"
                    class="mx-auto" />
                <b-button
                    :disabled="!hasItemsSelected"
                    :variant="deleteButtonVariant"
                    v-b-modal.confirmation-modal
                    class="mx-2">
                    {{ permanentlyDeleteText }} {{ deleteItemsText }}
                </b-button>
            </template>
        </b-modal>
        <b-modal
            id="confirmation-modal"
            :title="confirmationTitle"
            :ok-title="permanentlyDeleteText"
            :ok-variant="confirmButtonVariant"
            :ok-disabled="!confirmChecked"
            @show="resetConfirmationModal"
            @ok="onConfirmPurgeSelectedItems"
            centered>
            <b-form-checkbox id="confirm-delete-checkbox" v-model="confirmChecked">
                {{ agreementText }}
            </b-form-checkbox>
        </b-modal>
    </div>
</template>

<script>
import _l from "utils/localization";
import { bytesToString } from "utils/utils";
import UtcDate from "components/UtcDate";

export default {
    components: {
        UtcDate,
    },
    props: {
        title: {
            type: String,
            required: false,
            default: "Purgeable items",
        },
        items: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            fields: [
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
                    formatter: this.toNiceSize,
                },
                {
                    label: "Updated",
                    key: "update_time",
                    sortable: true,
                },
            ],
            sortBy: "size",
            sortDesc: true,
            perPage: 3,
            currentPage: 1,
            totalRows: 1,
            allSelected: false,
            indeterminate: false,
            selectedItems: [],
            confirmChecked: false,
            permanentlyDeleteText: _l("Permanently delete"),
            agreementText: _l("I understand that once I delete the items, they cannot be recovered."),
        };
    },
    methods: {
        toNiceSize(sizeInBytes) {
            return bytesToString(sizeInBytes, true);
        },
        toggleSelectAll(checked) {
            this.selectedItems = checked ? this.items : [];
        },
        hideModal() {
            this.$refs["purgeable-details-modal"].hide();
        },
        resetModal() {
            this.selectedItems = [];
        },
        resetConfirmationModal() {
            this.confirmChecked = false;
        },
        onConfirmPurgeSelectedItems() {
            this.$emit("onConfirmPurgeSelectedItems", this.selectedItems);
            this.hideModal();
        },
    },
    computed: {
        /** @returns {Number} */
        selectedItemCount() {
            return this.selectedItems.length;
        },
        /** @returns {Boolean} */
        hasItemsSelected() {
            return this.selectedItems.length > 0;
        },
        /** @returns {Boolean} */
        hasPages() {
            return this.totalRows > this.perPage;
        },
        /** @returns {String} */
        confirmationTitle() {
            return `Delete ${this.selectedItemCount} items?`;
        },
        /** @returns {String} */
        deleteButtonVariant() {
            return this.hasItemsSelected ? "danger" : "";
        },
        /** @returns {String} */
        deleteItemsText() {
            return this.hasItemsSelected ? `${this.selectedItemCount} items` : "";
        },
        /** @returns {String} */
        confirmButtonVariant() {
            return this.confirmChecked ? "danger" : "";
        },
    },
    watch: {
        items(newVal) {
            this.totalRows = newVal.length;
        },
        selectedItems(newVal) {
            if (newVal.length === 0) {
                this.indeterminate = false;
                this.allSelected = false;
            } else if (newVal.length === this.items.length) {
                this.indeterminate = false;
                this.allSelected = true;
            } else {
                this.indeterminate = true;
                this.allSelected = false;
            }
        },
    },
};
</script>

