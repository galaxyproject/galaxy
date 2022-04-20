<template>
    <HistoryItemsProvider
        :key="historyId"
        v-slot="{ loading, result: payload, count: totalItemsInQuery }"
        :history-id="historyId"
        :offset="offset"
        :filter-text="filterText">
        <ExpandedItems
            v-slot="{ expandedCount, isExpanded, setExpanded, collapseAll }"
            :scope-key="historyId"
            :get-item-key="(item) => item.type_id">
            <SelectedItems
                v-slot="{
                    selectedItems,
                    showSelection,
                    isQuerySelection,
                    selectionSize,
                    setShowSelection,
                    selectAllInCurrentQuery,
                    selectItems,
                    isSelected,
                    setSelected,
                    resetSelection,
                }"
                :scope-key="queryKey"
                :get-item-key="(item) => item.type_id"
                :filter-text="filterText">
                <section class="history-layout d-flex flex-column">
                    <slot name="navigation" :history="history" />
                    <HistoryFilters
                        class="content-operations-filters mx-3"
                        :filter-text.sync="filterText"
                        :show-advanced.sync="showAdvanced" />
                    <section v-if="!showAdvanced">
                        <HistoryDetails :history="history" @detailsFilter="onDetailsFilter" v-on="$listeners" />
                        <HistoryMessages class="m-2" :history="history" />
                        <HistoryOperations
                            :history="history"
                            :show-selection="showSelection"
                            :expanded-count="expandedCount"
                            :has-matches="hasMatches(payload)"
                            @update:show-selection="setShowSelection"
                            @collapse-all="collapseAll">
                            <template v-slot:selection-operations>
                                <HistorySelectionOperations
                                    v-if="showSelection"
                                    :history="history"
                                    :filter-text="filterText"
                                    :content-selection="selectedItems"
                                    :selection-size="selectionSize"
                                    :is-query-selection="isQuerySelection"
                                    :total-items-in-query="totalItemsInQuery"
                                    @update:content-selection="selectItems"
                                    @hide-selection="onHideSelection"
                                    @reset-selection="resetSelection" />
                                <HistorySelectionStatus
                                    v-if="showSelection"
                                    :selection-size="selectionSize"
                                    @select-all="selectAllInCurrentQuery(payload, totalItemsInQuery)"
                                    @reset-selection="resetSelection" />
                            </template>
                        </HistoryOperations>
                    </section>
                    <section v-if="!showAdvanced" class="position-relative flex-grow-1 scroller">
                        <div>
                            <div v-if="payload && payload.length == 0">
                                <b-alert v-if="loading" class="m-2" variant="info" show>
                                    <LoadingSpan message="Loading History" />
                                </b-alert>
                                <div v-else>
                                    <HistoryEmpty v-if="queryDefault" class="m-2" />
                                    <b-alert v-else class="m-2" variant="info" show>
                                        No data found for selected filter.
                                    </b-alert>
                                </div>
                            </div>
                            <Listing v-else :items="payload" :query-key="queryKey" @scroll="onScroll">
                                <template v-slot:item="{ item }">
                                    <ContentItem
                                        v-if="!invisible[item.hid]"
                                        :id="item.hid"
                                        :item="item"
                                        :name="item.name"
                                        :expand-dataset="isExpanded(item)"
                                        :is-dataset="isDataset(item)"
                                        :selected="isSelected(item)"
                                        :selectable="showSelection"
                                        @update:expand-dataset="setExpanded(item, $event)"
                                        @update:selected="setSelected(item, $event)"
                                        @view-collection="$emit('view-collection', item)"
                                        @delete="onDelete(item)"
                                        @undelete="onUndelete(item)"
                                        @unhide="onUnhide(item)" />
                                </template>
                            </Listing>
                        </div>
                    </section>
                </section>
            </SelectedItems>
        </ExpandedItems>
    </HistoryItemsProvider>
</template>

<script>
import Vue from "vue";
import { HistoryItemsProvider } from "components/providers/storeProviders";
import LoadingSpan from "components/LoadingSpan";
import ContentItem from "components/History/Content/ContentItem";
import { deleteContent, updateContentFields } from "components/History/model/queries";
import ExpandedItems from "components/History/Content/ExpandedItems";
import SelectedItems from "components/History/Content/SelectedItems";
import Listing from "components/History/Layout/Listing";
import HistoryOperations from "./HistoryOperations/Index";
import HistoryDetails from "./HistoryDetails";
import HistoryEmpty from "./HistoryEmpty";
import HistoryFilters from "./HistoryFilters";
import HistoryMessages from "./HistoryMessages";
import HistorySelectionOperations from "./HistoryOperations/SelectionOperations";
import HistorySelectionStatus from "./HistoryOperations/SelectionStatus";

export default {
    components: {
        ContentItem,
        ExpandedItems,
        HistoryMessages,
        HistoryDetails,
        HistoryEmpty,
        HistoryFilters,
        HistoryItemsProvider,
        HistoryOperations,
        HistorySelectionOperations,
        HistorySelectionStatus,
        LoadingSpan,
        Listing,
        SelectedItems,
    },
    props: {
        history: { type: Object, required: true },
    },
    data() {
        return {
            filterText: "",
            invisible: {},
            offset: 0,
            showAdvanced: false,
        };
    },
    computed: {
        /** @returns {String} */
        historyId() {
            return this.history.id;
        },
        /** @returns {String} */
        queryKey() {
            return `${this.historyId}-${this.filterText}`;
        },
        /** @returns {Boolean} */
        queryDefault() {
            return !this.filterText;
        },
        /** @returns {Boolean} */
        hasFilters() {
            return !this.queryDefault;
        },
    },
    watch: {
        queryKey() {
            this.invisible = {};
            this.offset = 0;
        },
    },
    methods: {
        hasMatches(payload) {
            return !!payload && payload.length > 0;
        },
        isDataset(item) {
            return item.history_content_type == "dataset";
        },
        onDelete(item) {
            this.setInvisible(item);
            deleteContent(item);
        },
        onHideSelection(selectedItems) {
            selectedItems.forEach((item) => {
                this.setInvisible(item);
            });
        },
        onScroll(offset) {
            this.offset = offset;
        },
        onUndelete(item) {
            this.setInvisible(item);
            updateContentFields(item, { deleted: false });
        },
        onUnhide(item) {
            this.setInvisible(item);
            updateContentFields(item, { visible: true });
        },
        setInvisible(item) {
            Vue.set(this.invisible, item.hid, true);
        },
        onDetailsFilter(newFilterText) {
            this.filterText = newFilterText;
        },
    },
};
</script>
