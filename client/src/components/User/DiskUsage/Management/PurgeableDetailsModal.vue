<template>
    <div>
        <b-modal id="purgeable-details-modal" :title="title" size="xl">
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
                        @change="toggleAll"></b-form-checkbox>
                </template>
                <template v-slot:cell(selected)="data">
                    <b-form-checkbox
                        v-model="selectedItemIds"
                        :checked="allSelected"
                        :key="data.index"
                        :value="data.item['id']"></b-form-checkbox>
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
                    :per-page="perPage"></b-pagination>
                <b-button v-if="hasItemsSelected" class="mx-2" variant="danger" v-b-modal.confirmation-modal>
                    Permanently delete {{ selectedItemCount }} items
                </b-button>
            </template>
        </b-modal>
        <b-modal
            id="confirmation-modal"
            :title="confirmationTitle"
            ok-title="Permanently delete"
            ok-variant="danger"
            :ok-disabled="!confirmChecked"
            size="sm"
            centered>
            <b-form-checkbox id="confirm-delete-checkbox" v-model="confirmChecked">
                I understand that once I delete the items, they cannot be recovered.
            </b-form-checkbox>
        </b-modal>
    </div>
</template>

<script>
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
            selectedItemIds: [],
            confirmChecked: false,
        };
    },
    methods: {
        toNiceSize(sizeInBytes) {
            return bytesToString(sizeInBytes, true);
        },
        toggleAll(checked) {
            this.selectedItemIds = checked ? this.items.reduce((acc, item) => [...acc, item["id"]], []) : [];
            console.log("Selected ITEMS: ", this.selectedItemIds);
        },
        onConfirmDeleteSelectedItems() {
            this.$emit("onConfirmDeleteSelectedItems", this.selectedItemIds);
        },
    },
    computed: {
        /** @returns {Number} */
        selectedItemCount() {
            return this.selectedItemIds.length;
        },
        /** @returns {Boolean} */
        hasItemsSelected() {
            return this.selectedItemIds.length > 0;
        },
        /** @returns {Boolean} */
        hasPages() {
            return this.totalRows > this.perPage;
        },
        /** @returns {String} */
        confirmationTitle() {
            return `Delete ${this.selectedItemCount} items?`;
        },
    },
    watch: {
        items(newVal) {
            this.totalRows = newVal.length;
        },
        selectedItemIds(newVal) {
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

