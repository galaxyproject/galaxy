<template>
    <HistoryItemsProvider
        :key="historyId"
        v-slot="{ loading, result: itemsLoaded, count: totalItemsInQuery }"
        :history-id="historyId"
        :offset="offset"
        :update-time="history.update_time"
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
                    isSelected,
                    setSelected,
                    resetSelection,
                }"
                :scope-key="queryKey"
                :get-item-key="(item) => item.type_id"
                :filter-text="filterText"
                :total-items-in-query="totalItemsInQuery"
                @query-selection-break="querySelectionBreak = true">
                <section class="history-layout d-flex flex-column">
                    <slot name="navigation" :history="history" />
                    <HistoryFilters
                        class="content-operations-filters mx-3"
                        :filter-text.sync="filterText"
                        :show-advanced.sync="showAdvanced" />
                    <section v-if="!showAdvanced">
                        <HistoryDetails :history="history" @update:history="$emit('updateHistory', $event)" />
                        <HistoryMessages :history="history" />
                        <HistoryCounter
                            :history="history"
                            :last-checked="lastChecked"
                            :filter-text.sync="filterText"
                            @reloadContents="reloadContents" />
                        <HistoryOperations
                            :history="history"
                            :show-selection="showSelection"
                            :expanded-count="expandedCount"
                            :has-matches="hasMatches(itemsLoaded)"
                            :operation-running.sync="operationRunning"
                            @update:show-selection="setShowSelection"
                            @collapse-all="collapseAll">
                            <template v-slot:selection-operations>
                                <HistorySelectionOperations
                                    :history="history"
                                    :filter-text="filterText"
                                    :content-selection="selectedItems"
                                    :selection-size="selectionSize"
                                    :is-query-selection="isQuerySelection"
                                    :total-items-in-query="totalItemsInQuery"
                                    :operation-running.sync="operationRunning"
                                    @update:show-selection="setShowSelection"
                                    @operation-error="onOperationError"
                                    @hide-selection="onHideSelection"
                                    @reset-selection="resetSelection" />
                                <HistorySelectionStatus
                                    v-if="showSelection"
                                    :selection-size="selectionSize"
                                    @select-all="selectAllInCurrentQuery(itemsLoaded)"
                                    @reset-selection="resetSelection" />
                            </template>
                        </HistoryOperations>
                        <SelectionChangeWarning :query-selection-break="querySelectionBreak" />
                        <OperationErrorDialog
                            v-if="operationError"
                            :operation-error="operationError"
                            @hide="operationError = null" />
                    </section>
                    <section v-if="!showAdvanced" class="position-relative flex-grow-1 scroller">
                        <div>
                            <div v-if="itemsLoaded && itemsLoaded.length == 0 && loading">
                                <b-alert class="m-2" variant="info" show>
                                    <LoadingSpan message="Loading History" />
                                </b-alert>
                            </div>
                            <b-alert v-else-if="isProcessing" class="m-2" variant="info" show>
                                <LoadingSpan message="Processing operation" />
                            </b-alert>
                            <div v-else-if="totalItemsInQuery == 0">
                                <HistoryEmpty v-if="queryDefault" class="m-2" />
                                <b-alert v-else class="m-2" variant="info" show>
                                    No data found for selected filter.
                                </b-alert>
                            </div>
                            <Listing
                                v-else
                                :offset="listOffset"
                                :items="itemsLoaded"
                                :query-key="queryKey"
                                @scroll="onScroll">
                                <template v-slot:item="{ item, currentOffset }">
                                    <ContentItem
                                        v-if="!invisible[item.hid]"
                                        is-history-item
                                        :id="item.hid"
                                        :item="item"
                                        :name="item.name"
                                        :expand-dataset="isExpanded(item)"
                                        :is-dataset="isDataset(item)"
                                        :highlight="getHighlight(item)"
                                        :selected="isSelected(item)"
                                        :selectable="showSelection"
                                        @tag-click="onTagClick"
                                        @tag-change="onTagChange"
                                        @toggleHighlights="toggleHighlights"
                                        @update:expand-dataset="setExpanded(item, $event)"
                                        @update:selected="setSelected(item, $event)"
                                        @view-collection="$emit('view-collection', item, currentOffset)"
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
import { getHighlights } from "components/History/Content/model/highlights";
import ExpandedItems from "components/History/Content/ExpandedItems";
import SelectedItems from "components/History/Content/SelectedItems";
import Listing from "components/History/Layout/Listing";
import HistoryCounter from "./HistoryCounter";
import HistoryOperations from "./HistoryOperations/Index";
import HistoryDetails from "./HistoryDetails";
import HistoryEmpty from "./HistoryEmpty";
import HistoryFilters from "./HistoryFilters/HistoryFilters";
import HistoryMessages from "./HistoryMessages";
import HistorySelectionOperations from "./HistoryOperations/SelectionOperations";
import HistorySelectionStatus from "./HistoryOperations/SelectionStatus";
import SelectionChangeWarning from "./HistoryOperations/SelectionChangeWarning";
import OperationErrorDialog from "./HistoryOperations/OperationErrorDialog";
import { rewatchHistory } from "store/historyStore/model/watchHistory";

export default {
    components: {
        ContentItem,
        ExpandedItems,
        HistoryCounter,
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
        SelectionChangeWarning,
        OperationErrorDialog,
    },
    props: {
        listOffset: { type: Number, default: 0 },
        history: { type: Object, required: true },
    },
    data() {
        return {
            filterText: "",
            highlights: {},
            highlightsKey: null,
            invisible: {},
            offset: 0,
            showAdvanced: false,
            operationRunning: null,
            operationError: null,
            querySelectionBreak: false,
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
        /** @returns {Boolean} */
        isProcessing() {
            return this.operationRunning >= this.history.update_time;
        },
        /** @returns {Date} */
        lastChecked() {
            return this.$store.getters.getLastCheckedTime();
        },
    },
    watch: {
        queryKey() {
            this.invisible = {};
            this.offset = 0;
            this.resetHighlights();
        },
        historyId(newVal, oldVal) {
            if (newVal !== oldVal) {
                this.operationRunning = null;
                this.resetHighlights();
            }
        },
    },
    methods: {
        getHighlight(item) {
            return this.highlights[this.getItemKey(item)];
        },
        getItemKey(item) {
            return `${item.id}-${item.history_content_type}`;
        },
        hasMatches(items) {
            return !!items && items.length > 0;
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
        reloadContents() {
            rewatchHistory();
        },
        setInvisible(item) {
            Vue.set(this.invisible, item.hid, true);
        },
        onTagChange(item, newTags) {
            item.tags = newTags;
        },
        onTagClick(tag) {
            if (this.filterText == "tag:" + tag) {
                this.filterText = "";
            } else {
                this.filterText = "tag:" + tag;
            }
        },
        onOperationError(error) {
            console.debug("OPERATION ERROR", error);
            this.operationError = error;
        },
        async toggleHighlights(item) {
            const key = this.getItemKey(item);
            if (this.highlightsKey != key) {
                this.highlightsKey = key;
                this.highlights = await getHighlights(item, key);
            } else {
                this.resetHighlights();
            }
        },
        resetHighlights() {
            this.highlights = {};
            this.highlightsKey = null;
        },
    },
};
</script>
