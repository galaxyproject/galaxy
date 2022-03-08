<template>
    <div>
        <div></div>
        <b-modal id="select-history-modal" v-model="showModalModel" title="Switch to History" @hidden="toggleHidden">
            <b-form-input id="filter-input" v-model="filter" type="search" placeholder="Type to Search"></b-form-input>
            <b-table
                id="history-table"
                striped
                hover
                :fields="fields"
                :items="historyRows"
                :filter="filter"
                :per-page="perPage"
                :current-page="currentPage"
                @filtered="onFiltered"
                @row-clicked="switchToHistory"
                sticky-header="50vh">
                <template v-slot:cell(tags)="row">
                    <!-- just display tags, don't allow editing -->
                    <stateless-tags :value="row.item.tags" :disabled="true" />
                </template>
                <template v-slot:cell(update_time)="data">
                    <UtcDate :date="data.value" mode="elapsed" />
                </template>
            </b-table>
            <template v-slot:modal-footer>
                <b-pagination v-model="currentPage" :total-rows="totalRows" :per-page="perPage"></b-pagination>
            </template>
        </b-modal>
    </div>
</template>

<script>
import { StatelessTags } from "components/Tags";
import UtcDate from "components/UtcDate";
import Vue from "vue";

export default {
    components: {
        StatelessTags,
        UtcDate,
    },
    props: {
        currentHistory: { type: Object, required: true },
        histories: { type: Array, default: () => [] },
        showModal: { type: Boolean, default: false },
    },
    data() {
        return {
            fields: [
                {
                    key: "name",
                    sortable: true,
                },
                {
                    key: "tags",
                    sortable: true,
                },
                {
                    label: "Updated",
                    key: "update_time",
                    sortable: true,
                },
            ],
            sortBy: "update_time",
            sortDesc: true,
            filter: null,
            rows: [],
            perPage: 50,
            currentPage: 1,
            totalRows: 1,
            historyRows: [],
            currentHistoryRow: {},
            showModalModel: false,
        };
    },
    watch: {
        showModal(newval) {
            this.showModalModel = newval;
        },
        histories(newval) {
            if (!this.filter) {
                this.totalRows = newval.length;
            }
            this.historyRows = newval.map((item) => {
                if (item.id == this.currentHistory.id) {
                    Vue.set(item, "_rowVariant", "success");
                    this.currentHistoryRow = item;
                }
                return item;
            });
        },
    },
    methods: {
        toggleHidden() {
            this.$emit("hideModal");
        },
        onFiltered(filteredItems) {
            // Trigger pagination to update the number of buttons/pages due to filtering
            if (this.totalRows != filteredItems.length) {
                /* According to https://bootstrap-vue.org/docs/components/table#filter-events
                   the filtered event should only emit when the length of the filtered items
                   changes. Selecting a new active history will change the histories props
                   (the active history will contain more fields). So we only reset the pagination
                   if the totalRows have actually changed.
                */
                this.totalRows = filteredItems.length;
                this.currentPage = 1;
            }
        },
        switchToHistory(history, index) {
            this.$emit("update:currentHistory", history);
            this.currentHistoryRow._rowVariant = null;
            Vue.set(history, "_rowVariant", "success");
            this.currentHistoryRow = history;
        },
    },
};
</script>
