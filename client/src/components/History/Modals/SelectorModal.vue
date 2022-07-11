<template>
    <b-modal ref="modal" v-bind="$attrs" :title="'Switch to History' | l" v-on="$listeners">
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
            :items="formattedItems"
            :per-page="perPage"
            :current-page="currentPage"
            :selectable="true"
            :sort-by.sync="sortBy"
            :sort-desc.sync="sortDesc"
            :sort-compare="currentFirstSortCompare"
            select-mode="single"
            selected-variant="success"
            @row-selected="switchToHistory"
            @filtered="onFiltered">
            <template v-slot:cell(tags)="row">
                <stateless-tags :value="row.item.tags" :disabled="true" />
            </template>
            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
        </b-table>

        <template v-slot:modal-footer>
            <b-pagination v-model="currentPage" :total-rows="totalRows" :per-page="perPage" />
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
        };
    },
    computed: {
        formattedItems() {
            return this.histories.map((item) => {
                if (item.id == this.currentHistoryId) {
                    item._rowVariant = "success";
                }
                return item;
            });
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
            { key: "update_time", label: "Updated", sortable: true },
        ];
    },
    methods: {
        switchToHistory(selected) {
            if (selected.length == 1) {
                this.$emit("selectHistory", selected[0]);
            }
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
