<template>
    <b-modal ref="modal" v-bind="$attrs" :title="'Switch to History' | l" v-on="$listeners">
        <b-form-group :description="'Filter histories' | l">
            <b-input v-model="filter" :placeholder="'Search Filter' | l" />
        </b-form-group>

        <b-table
            ref="history-list"
            v-model="currentRows"
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
            select-mode="single"
            selected-variant="success"
            @row-selected="switchToHistory">
            <template v-slot:cell(tags)="row">
                <stateless-tags :value="row.item.tags" :disabled="true" />
            </template>
            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
        </b-table>

        <template v-slot:modal-footer>
            <b-pagination v-model="currentPage" :total-rows="filteredRowCount" :per-page="perPage"></b-pagination>
        </template>
    </b-modal>
</template>

<script>
import { StatelessTags } from "components/Tags";
import UtcDate from "components/UtcDate";
import { debounce } from "underscore";

export default {
    components: {
        StatelessTags,
        UtcDate,
    },
    props: {
        currentHistory: { type: Object, required: true },
        histories: { type: Array, default: () => [] },
        perPage: { type: Number, required: false, default: 50 },
    },
    data() {
        return {
            filter: null,
            currentPage: 1,
            currentRows: [],
        };
    },
    computed: {
        filteredRowCount() {
            return this.currentRows.length;
        },
        selectedIndex() {
            return this.currentRows.findIndex((h) => h.id == this.currentHistory.id);
        },
    },
    watch: {
        currentRows() {
            this.selectCurrentRow();
        },
        filteredRowCount(newVal, oldVal) {
            if (newVal != oldVal) {
                this.currentPage = 1;
            }
        },
        selectedIndex(idx, oldIdx) {
            if (idx != oldIdx) {
                this.debounceSelectCurrentRow();
            }
        },
    },
    created() {
        this.fields = [
            { key: "name", sortable: true },
            { key: "tags", sortable: true },
            { key: "update_time", label: "Updated", sortable: true },
        ];
        this.debounceSelectCurrentRow = debounce(this.selectCurrentRow, 100);
    },
    methods: {
        switchToHistory(selected) {
            if (selected.length == 1) {
                this.$emit("selectHistory", selected[0]);
            }
        },
        selectCurrentRow() {
            const idx = this.selectedIndex;
            const list = this.$refs["history-list"];
            if (list && idx > -1) {
                list.selectRow(idx);
            }
        },
    },
};
</script>
