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
                        <HistoryCounter :history="history" :filter-text.sync="filterText" />
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
                            <Listing v-else :items="itemsLoaded" :query-key="queryKey" @scroll="onScroll">
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
import HistoryCounter from "./HistoryCounter";
import HistoryOperations from "./HistoryOperations/Index";
import HistoryDetails from "./HistoryDetails";
import HistoryEmpty from "./HistoryEmpty";
import HistoryFilters from "./HistoryFilters";
import HistoryMessages from "./HistoryMessages";
import HistorySelectionOperations from "./HistoryOperations/SelectionOperations";
import HistorySelectionStatus from "./HistoryOperations/SelectionStatus";
import SelectionChangeWarning from "./HistoryOperations/SelectionChangeWarning";
import OperationErrorDialog from "./HistoryOperations/OperationErrorDialog";

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
        history: { type: Object, required: true },
    },
    data() {
        return {
            filterText: "",
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
    },
    watch: {
        queryKey() {
            this.invisible = {};
            this.offset = 0;
        },
        historyId(newVal, oldVal) {
            if (newVal !== oldVal) {
                this.operationRunning = null;
            }
        },
    },
    methods: {
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
        setInvisible(item) {
            Vue.set(this.invisible, item.hid, true);
        },
        onOperationError(error) {
            console.debug("OPERATION ERROR", error);
            this.operationError = error;
        },
    },
};
</script>
