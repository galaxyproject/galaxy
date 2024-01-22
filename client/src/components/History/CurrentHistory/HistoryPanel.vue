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
            :total-items-in-query="totalMatchesCount"
            @query-selection-break="querySelectionBreak = true">
            <section
                class="history-layout d-flex flex-column w-100"
                @drop.prevent="onDrop"
                @dragenter.prevent="onDragEnter"
                @dragover.prevent
                @dragleave.prevent="onDragLeave">
                <slot name="navigation" :history="history" />
                <FilterMenu
                    v-if="filterable"
                    class="content-operations-filters mx-3"
                    name="History Items"
                    placeholder="search datasets"
                    :filter-class="filterClass"
                    :filter-text.sync="filterText"
                    :loading="loading"
                    :search-error="searchError"
                    :show-advanced.sync="showAdvanced" />
                <section v-if="!showAdvanced">
                    <HistoryDetails :history="history" :writeable="writable" @update:history="updateHistory($event)" />
                    <HistoryMessages :history="history" />
                    <HistoryCounter
                        :history="history"
                        :is-watching="isWatching"
                        :last-checked="lastCheckedTime"
                        :show-controls="showControls"
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
                                :total-items-in-query="totalMatchesCount"
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
                    <HistoryDropZone v-if="showDropZone" />
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
                            <HistoryEmpty v-if="queryDefault" :writable="writable" class="m-2" />
                            <b-alert v-else-if="formattedSearchError" class="m-2" variant="danger" show>
                                Error in filter:
                                <a href="javascript:void(0)" @click="showAdvanced = true">
                                    {{ formattedSearchError.filter }}'{{ formattedSearchError.value }}'
                                </a>
                            </b-alert>
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
                                    @tag-click="updateFilterVal('tag', $event)"
                                    @tag-change="onTagChange"
                                    @toggleHighlights="updateFilterVal('related', item.hid)"
                                    @update:expand-dataset="setExpanded(item, $event)"
                                    @update:selected="setSelected(item, $event)"
                                    @view-collection="$emit('view-collection', item, currentOffset)"
                                    @delete="onDelete"
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
import FilterMenu from "components/Common/FilterMenu";
import ContentItem from "components/History/Content/ContentItem";
import ExpandedItems from "components/History/Content/ExpandedItems";
import SelectedItems from "components/History/Content/SelectedItems";
import { HistoryFilters } from "components/History/HistoryFilters";
import ListingLayout from "components/History/Layout/ListingLayout";
import { deleteContent, updateContentFields } from "components/History/model/queries";
import LoadingSpan from "components/LoadingSpan";
import { Toast } from "composables/toast";
import { mapActions, mapState, storeToRefs } from "pinia";
import { rewatchHistory } from "store/historyStore/model/watchHistory";
import { useHistoryItemsStore } from "stores/historyItemsStore";
import { useHistoryStore } from "stores/historyStore";
import { getOperatorForAlias } from "utils/filtering";
import Vue from "vue";

import { copyDataset } from "@/api/datasets";

import HistoryCounter from "./HistoryCounter";
import HistoryDetails from "./HistoryDetails";
import HistoryDropZone from "./HistoryDropZone";
import HistoryEmpty from "./HistoryEmpty";
import HistoryMessages from "./HistoryMessages";
import HistoryOperations from "./HistoryOperations/HistoryOperations";
import OperationErrorDialog from "./HistoryOperations/OperationErrorDialog";
import SelectionChangeWarning from "./HistoryOperations/SelectionChangeWarning";
import HistorySelectionOperations from "./HistoryOperations/SelectionOperations";
import HistorySelectionStatus from "./HistoryOperations/SelectionStatus";

export default {
    components: {
        ContentItem,
        ExpandedItems,
        FilterMenu,
        HistoryCounter,
        HistoryMessages,
        HistoryDetails,
        HistoryDropZone,
        HistoryEmpty,
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
    setup() {
        const { currentFilterText, currentHistoryId } = storeToRefs(useHistoryStore());
        const { lastCheckedTime, totalMatchesCount, isWatching } = storeToRefs(useHistoryItemsStore());
        return { currentFilterText, currentHistoryId, lastCheckedTime, totalMatchesCount, isWatching };
    },
    data() {
        return {
            filterText: "",
            filterClass: HistoryFilters,
            invisible: {},
            loading: false,
            offset: 0,
            searchError: null,
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
        /** @returns {Object} */
        formattedSearchError() {
            if (this.searchError) {
                const { column, col, operation, op, value, val, err_msg, ValueError } = this.searchError;
                const alias = operation || op;
                const operator = alias ? getOperatorForAlias(alias) : ":";
                const formatted = {
                    filter: `${column || col}${operator}`,
                    value: value || val,
                    msg: err_msg,
                    typeError: ValueError,
                };
                return formatted;
            } else {
                return null;
            }
        },
        /** @returns {String} */
        storeFilterText() {
            if (this.historyId === this.currentHistoryId) {
                return this.currentFilterText || "";
            } else {
                return "";
            }
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
        filterText(newVal) {
            if (this.filterable) {
                this.setFilterText(this.historyId, newVal);
            }
        },
        storeFilterText(newVal) {
            if (this.filterable) {
                this.filterText = newVal;
            }
        },
        offset() {
            this.loadHistoryItems();
        },
        async historyUpdateTime() {
            await this.loadHistoryItems();
        },
        itemsLoaded(newItems) {
            if (this.invisible) {
                newItems.forEach((item) => {
                    if (this.invisible[item.hid]) {
                        Vue.set(this.invisible, item.hid, false);
                    }
                });
            }
        },
    },
    async mounted() {
        // `filterable` here indicates if this is the current history panel
        if (this.filterable && !this.filter) {
            this.filterText = this.storeFilterText;
        }
        await this.loadHistoryItems();
    },
    methods: {
        ...mapActions(useHistoryStore, ["loadHistoryById", "setFilterText", "updateHistory"]),
        ...mapActions(useHistoryItemsStore, ["fetchHistoryItems"]),
        getHighlight(item) {
            const highlightsKey = this.filterClass.getFilterValue(this.filterText, "related");
            if (!this.loading) {
                if (highlightsKey == item.hid) {
                    return "active";
                } else if (highlightsKey) {
                    if (item.hid > highlightsKey) {
                        return "output";
                    } else {
                        return "input";
                    }
                }
            } else {
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
                this.searchError = null;
            } catch (error) {
                if (error.response && error.response.data && error.response.data.err_msg) {
                    console.debug("HistoryPanel - Load items error:", error.response.data.err_msg);
                    this.searchError = error.response.data;
                } else {
                    console.debug("HistoryPanel - Load items error.", error);
                }
            } finally {
                this.loading = false;
            }
        },
        async onDelete(item, recursive = false) {
            this.loading = true;
            this.setInvisible(item);
            await deleteContent(item, { recursive: recursive });
            this.loading = false;
        },
        onHideSelection(selectedItems) {
            selectedItems.forEach((item) => {
                this.setInvisible(item);
            });
        },
        onScroll(offset) {
            this.offset = offset;
        },
        async onUndelete(item) {
            this.setInvisible(item);
            this.loading = true;
            await updateContentFields(item, { deleted: false });
            this.loading = false;
        },
        async onUnhide(item) {
            this.setInvisible(item);
            this.loading = true;
            await updateContentFields(item, { visible: true });
            this.loading = false;
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
        onOperationError(error) {
            console.debug("HistoryPanel - Operation error.", error);
            this.operationError = error;
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
        async onDrop(evt) {
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
                    try {
                        await copyDataset(data.id, this.historyId, data.history_content_type, dataSource);
                        if (data.history_content_type === "dataset") {
                            Toast.info("Dataset copied to history");
                        } else {
                            Toast.info("Collection copied to history");
                        }
                        this.loadHistoryById(this.historyId);
                    } catch (error) {
                        this.onError(error);
                    }
                }
            }
        },
        onError(error) {
            Toast.error(`${error}`);
        },
        updateFilterVal(newFilter, newVal) {
            this.filterText = this.filterClass.setFilterValue(this.filterText, newFilter, newVal);
        },
    },
};
</script>
