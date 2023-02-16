<template>
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
            <section
                class="history-layout d-flex flex-column w-100"
                @drop.prevent="onDrop"
                @dragenter.prevent="onDragEnter"
                @dragover.prevent
                @dragleave.prevent="onDragLeave">
                <slot name="navigation" :history="history" />
                <HistoryFilters
                    v-if="showControls"
                    class="content-operations-filters mx-3"
                    :filter-text.sync="filterText"
                    :show-advanced.sync="showAdvanced" />
                <section v-if="!showAdvanced">
                    <HistoryDetails
                        :history="history"
                        :writeable="writable"
                        @update:history="$emit('updateHistory', $event)" />
                    <HistoryMessages :history="history" />
                    <HistoryCounter
                        v-if="showControls"
                        :history="history"
                        :is-watching="isWatching"
                        :last-checked="lastChecked"
                        :filter-text.sync="filterText"
                        @reloadContents="reloadContents" />
                    <HistoryOperations
                        v-if="showControls"
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
                    <history-drop-zone v-if="showDropZone" />
                    <div>
                        <div v-if="loading && itemsLoaded && itemsLoaded.length === 0">
                            <b-alert class="m-2" variant="info" show>
                                <LoadingSpan message="Loading History" />
                            </b-alert>
                        </div>
                        <b-alert v-else-if="isProcessing" class="m-2" variant="info" show>
                            <LoadingSpan message="Processing operation" />
                        </b-alert>
                        <div v-else-if="itemsLoaded.length === 0">
                            <HistoryEmpty v-if="queryDefault" class="m-2" />
                            <b-alert v-else class="m-2" variant="info" show>
                                No data found for selected filter.
                            </b-alert>
                        </div>
                        <ListingLayout
                            v-else
                            :offset="listOffset"
                            :items="itemsLoaded"
                            :query-key="queryKey"
                            @scroll="onScroll">
                            <template v-slot:item="{ item, currentOffset }">
                                <ContentItem
                                    v-if="!invisible[item.hid]"
                                    :id="item.hid"
                                    is-history-item
                                    :item="item"
                                    :name="item.name"
                                    :writable="writable"
                                    :expand-dataset="isExpanded(item)"
                                    :is-dataset="isDataset(item)"
                                    :highlight="getHighlight(item)"
                                    :selected="isSelected(item)"
                                    :selectable="showSelection"
                                    :filterable="filterable"
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
                        </ListingLayout>
                    </div>
                </section>
            </section>
        </SelectedItems>
    </ExpandedItems>
</template>

<script>
import Vue from "vue";
import { Toast } from "composables/toast";
import { mapActions as vuexMapActions } from "vuex";
import { mapActions, mapState, storeToRefs } from "pinia";
import { useHistoryItemsStore } from "stores/history/historyItemsStore";
import LoadingSpan from "components/LoadingSpan";
import ContentItem from "components/History/Content/ContentItem";
import { deleteContent, updateContentFields } from "components/History/model/queries";
import ExpandedItems from "components/History/Content/ExpandedItems";
import SelectedItems from "components/History/Content/SelectedItems";
import ListingLayout from "components/History/Layout/ListingLayout";
import HistoryCounter from "./HistoryCounter";
import HistoryOperations from "./HistoryOperations/Index";
import HistoryDetails from "./HistoryDetails";
import HistoryDropZone from "./HistoryDropZone";
import HistoryEmpty from "./HistoryEmpty";
import HistoryFilters from "./HistoryFilters/HistoryFilters";
import HistoryMessages from "./HistoryMessages";
import HistorySelectionOperations from "./HistoryOperations/SelectionOperations";
import HistorySelectionStatus from "./HistoryOperations/SelectionStatus";
import SelectionChangeWarning from "./HistoryOperations/SelectionChangeWarning";
import OperationErrorDialog from "./HistoryOperations/OperationErrorDialog";
import { rewatchHistory } from "store/historyStore/model/watchHistory";
import { copyDataset } from "components/Dataset/services";

export default {
    components: {
        ContentItem,
        ExpandedItems,
        HistoryCounter,
        HistoryMessages,
        HistoryDetails,
        HistoryDropZone,
        HistoryEmpty,
        HistoryFilters,
        HistoryOperations,
        HistorySelectionOperations,
        HistorySelectionStatus,
        LoadingSpan,
        ListingLayout,
        SelectedItems,
        SelectionChangeWarning,
        OperationErrorDialog,
    },
    props: {
        listOffset: { type: Number, default: 0 },
        history: { type: Object, required: true },
        filter: { type: String, default: "" },
        writable: { type: Boolean, default: true },
        showControls: { type: Boolean, default: true },
        filterable: { type: Boolean, default: false },
    },
    data() {
        return {
            error: null,
            filterText: "",
            highlightsKey: null,
            invisible: {},
            loading: false,
            offset: 0,
            showAdvanced: false,
            showDropZone: false,
            operationRunning: null,
            operationError: null,
            querySelectionBreak: false,
        };
    },
    computed: {
        ...mapState(useHistoryItemsStore, ["getHistoryItems"]),
        /** @returns {String} */
        historyId() {
            return this.history.id;
        },
        /** @returns {Date} */
        historyUpdateTime() {
            return this.history.update_time;
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
        /** @returns {Array} */
        itemsLoaded() {
            return this.getHistoryItems(this.historyId, this.filterText);
        },
        /** @returns {Date} */
        lastChecked() {
            const { getLastCheckedTime } = storeToRefs(useHistoryItemsStore());
            return getLastCheckedTime.value;
        },
        /** @returns {Number} */
        totalItemsInQuery() {
            const { getTotalMatchesCount } = storeToRefs(useHistoryItemsStore());
            return getTotalMatchesCount.value;
        },
        /** @returns {Boolean} */
        isWatching() {
            const { getWatchingVisibility } = storeToRefs(useHistoryItemsStore());
            return getWatchingVisibility.value;
        },
    },
    watch: {
        queryKey() {
            this.invisible = {};
            this.offset = 0;
            this.loadHistoryItems();
        },
        historyId(newVal, oldVal) {
            if (newVal !== oldVal) {
                this.operationRunning = null;
            }
        },
        filter(newVal) {
            this.filterText = newVal;
        },
        offset() {
            this.loadHistoryItems();
        },
        historyUpdateTime() {
            this.loadHistoryItems();
        },
    },
    async mounted() {
        await this.loadHistoryItems();
    },
    methods: {
        ...vuexMapActions("history", ["loadHistoryById"]),
        ...mapActions(useHistoryItemsStore, ["fetchHistoryItems"]),
        getHighlight(item) {
            if (this.filterText.includes("related:" + item.hid)) {
                this.highlightsKey = item.hid;
                return "active";
            } else if (this.filterText.includes("related:") && this.highlightsKey) {
                if (item.hid > this.highlightsKey) {
                    return "output";
                } else {
                    return "input";
                }
            } else {
                this.highlightsKey = null;
                return null;
            }
        },
        hasMatches(items) {
            return !!items && items.length > 0;
        },
        isDataset(item) {
            return item.history_content_type == "dataset";
        },
        async loadHistoryItems() {
            this.loading = true;
            try {
                await this.fetchHistoryItems(this.historyId, this.filterText, this.offset);
                this.error = null;
                this.loading = false;
            } catch (error) {
                console.debug("HistoryPanel - Load error.", error);
                this.error = error;
                this.loading = false;
            }
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
            console.debug("HistoryPanel - Operation error.", error);
            this.operationError = error;
        },
        toggleHighlights(item) {
            if (this.filterText == "related:" + item.hid) {
                this.filterText = "";
            } else {
                this.filterText = "related:" + item.hid;
            }
        },
        onDragEnter(e) {
            this.dragTarget = e.target;
            this.showDropZone = true;
        },
        onDragLeave(e) {
            if (this.dragTarget == e.target) {
                this.showDropZone = false;
            }
        },
        onDrop(evt) {
            this.showDropZone = false;
            let data;
            try {
                data = JSON.parse(evt.dataTransfer.getData("text"))[0];
            } catch (error) {
                // this was not a valid object for this dropzone, ignore
            }
            if (data) {
                const dataSource = data.history_content_type === "dataset" ? "hda" : "hdca";
                if (data.history_id != this.historyId) {
                    copyDataset(data.id, this.historyId, data.history_content_type, dataSource)
                        .then(() => {
                            if (data.history_content_type === "dataset") {
                                Toast.info("Dataset copied to history");
                            } else {
                                Toast.info("Collection copied to history");
                            }
                            this.loadHistoryById(this.historyId);
                        })
                        .catch((error) => {
                            this.onError(error);
                        });
                }
            }
        },
        onError(error) {
            Toast.error(error);
        },
    },
};
</script>
