<template>
    <HistoryItemsProvider
        :key="historyId"
        :history-id="historyId"
        :offset="offset"
        :filter-text="filterText"
        v-slot="{ loading, result: payload, count: totalItemsInQuery }">
        <ExpandedItems
            :scope-key="historyId"
            :get-item-key="(item) => item.type_id"
            v-slot="{ expandedCount, isExpanded, setExpanded, collapseAll }">
            <SelectedItems
                :scope-key="queryKey"
                :get-item-key="(item) => item.type_id"
                :filter-text="filterText"
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
                }">
                <section class="history-layout d-flex flex-column">
                    <slot name="navigation" :history="history" />
                    <HistoryFilters
                        class="content-operations-filters mx-3"
                        :filter-text.sync="filterText"
                        :show-advanced.sync="showAdvanced" />
                    <section v-if="!showAdvanced">
                        <HistoryDetails :history="history" v-on="$listeners" />
                        <HistoryMessages class="m-2" :history="history" />
                        <HistoryOperations
                            :history="history"
                            :show-selection="showSelection"
                            :expanded-count="expandedCount"
                            :has-matches="hasMatches(payload)"
                            @update:show-selection="setShowSelection"
                            @collapse-all="collapseAll" />
                        <HistorySelectionStatus
                            v-if="showSelection"
                            class="m-2"
                            :has-filters="hasFilters"
                            :selection-size="selectionSize"
                            :total-items-in-query="totalItemsInQuery"
                            @select-all="selectAllInCurrentQuery(payload, totalItemsInQuery)"
                            @clear-selection="resetSelection">
                            <template v-slot:selection-options>
                                <HistorySelectionOptions
                                    :history="history"
                                    :filter-text="filterText"
                                    :content-selection="selectedItems"
                                    :selection-size="selectionSize"
                                    :is-query-selection="isQuerySelection"
                                    :total-items-in-query="totalItemsInQuery"
                                    @update:content-selection="selectItems"
                                    @hide-selection="onHideSelection"
                                    @reset-selection="resetSelection" />
                            </template>
                        </HistorySelectionStatus>
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
                                        :item="item"
                                        :id="item.hid"
                                        :name="item.name"
                                        :expand-dataset="isExpanded(item)"
                                        :is-dataset="item.history_content_type == 'dataset'"
                                        :selected="isSelected(item)"
                                        :selectable="showSelection"
                                        @update:expand-dataset="setExpanded(item, $event)"
                                        @update:selected="setSelected(item, $event)"
                                        @view-collection="$emit('view-collection', item)"
                                        @delete="onDelete"
                                        @undelete="onUndelete"
                                        @unhide="onUnhide" />
                                </template>
                            </Listing>
                        </div>
                    </section>
                    <ToolHelpModal />
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
import ToolHelpModal from "components/History/Modals/ToolHelpModal";
import HistoryOperations from "./HistoryOperations";
import HistoryDetails from "./HistoryDetails";
import HistoryEmpty from "./HistoryEmpty";
import HistoryFilters from "./HistoryFilters";
import HistoryMessages from "./HistoryMessages";
import HistorySelectionOptions from "./HistorySelectionOptions";
import HistorySelectionStatus from "./HistorySelectionStatus";

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
        HistorySelectionOptions,
        HistorySelectionStatus,
        LoadingSpan,
        Listing,
        SelectedItems,
        ToolHelpModal,
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
    watch: {
        queryKey() {
            this.invisible = {};
            this.offset = 0;
        },
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
    methods: {
        hasMatches(payload) {
            return !!payload && payload.length > 0;
        },
        onScroll(offset) {
            this.offset = offset;
        },
        onHideSelection(selectedItems) {
            selectedItems.forEach((item) => {
                this.setInvisible(item);
            });
        },
        onDelete(item) {
            this.setInvisible(item);
            deleteContent(item);
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
    },
};
</script>
