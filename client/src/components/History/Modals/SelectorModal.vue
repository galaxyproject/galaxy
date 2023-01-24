<template>
    <b-modal ref="modal" v-bind="$attrs" :title="title | l" footer-class="justify-content-between" v-on="$listeners">
        <b-form-group :description="'Filter histories' | l">
            <b-form-input v-model="filter" type="search" :placeholder="'Search Filter' | l" />
        </b-form-group>

        <b-table
            striped
            hover
            sticky-header="50vh"
            primary-key="id"
            :fields="fields"
            :filter="filter"
            :items="histories"
            :per-page="perPage"
            :current-page="currentPage"
            :selectable="true"
            :sort-by.sync="sortBy"
            :sort-desc.sync="sortDesc"
            :sort-compare="currentFirstSortCompare"
            :select-mode="multiple ? 'multi' : 'single'"
            selected-variant="success"
            @row-selected="rowSelected"
            @filtered="onFiltered">
            <template v-slot:cell(name)="row">
                {{ row.item.name }} <i v-if="row.item.id === currentHistoryId"><b>(Current)</b></i>
            </template>
            <template v-slot:cell(tags)="row">
                <stateless-tags :value="row.item.tags" :disabled="true" />
            </template>
            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
        </b-table>
        <template v-slot:modal-footer>
            <b-pagination v-model="currentPage" :total-rows="totalRows" :per-page="perPage" />
            <b-button v-if="multiple" :disabled="isEmptySelection" variant="primary" @click="addSelected">
                Add Selected
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import { BModal, BFormGroup, BFormInput, BTable, BPagination } from "bootstrap-vue";
import { StatelessTags } from "components/Tags";
import UtcDate from "components/UtcDate";

export default {
    components: {
        StatelessTags,
        UtcDate,
        BModal,
        BFormGroup,
        BFormInput,
        BTable,
        BPagination,
    },
    props: {
        multiple: { type: Boolean, default: false },
        title: { type: String, default: "Switch to history" },
        currentHistoryId: { type: String, required: true },
        histories: { type: Array, default: () => [] },
        perPage: { type: Number, required: false, default: 50 },
    },
    data() {
        return {
            filter: null,
            currentPage: 1,
            totalRows: 0,
            sortBy: "update_time",
            sortDesc: true,
            selectedHistories: [],
        };
    },
    computed: {
        isEmptySelection() {
            return this.selectedHistories.length === 0;
        },
    },
    watch: {
        histories(newVal) {
            this.totalRows = newVal.length;
        },
    },
    created() {
        this.fields = [
            { key: "name", sortable: true },
            { key: "tags", sortable: true },
            { key: "count", label: "Items", sortable: true },
            { key: "update_time", label: "Updated", sortable: true },
        ];
    },
    methods: {
        rowSelected(selected) {
            if (this.multiple) {
                this.selectedHistories = selected;
            } else if (selected.length === 1) {
                this.$emit("selectHistory", selected[0]);
                this.$refs.modal.hide();
            }
        },
        addSelected() {
            this.$emit("selectHistories", this.selectedHistories);
            this.$refs.modal.hide();
        },
        onFiltered(filteredItems) {
            this.totalRows = filteredItems.length;
            this.currentPage = 1;
        },
        /** Make the current history appear always first when sorting. */
        currentFirstSortCompare(a, b, key, sortDesc) {
            if (a.id == this.currentHistoryId) {
                return sortDesc ? 1 : -1;
            } else if (b.id == this.currentHistoryId) {
                return sortDesc ? -1 : 1;
            } else {
                // Fallback to default sorting
                return false;
            }
        },
    },
};
</script>
