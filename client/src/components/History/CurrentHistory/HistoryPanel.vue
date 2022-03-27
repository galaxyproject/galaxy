<template>
    <HistoryItemsProvider
        :key="history.id"
        :history-id="historyId"
        :offset="offset"
        :filter-text="params.filterText"
        :show-deleted="params.showDeleted"
        :show-hidden="params.showHidden"
        v-slot="{ loading, result: payload }">
        <ExpandedItems
            :scope-key="history.id"
            :get-item-key="(item) => item.type_id"
            v-slot="{ expandedCount, isExpanded, setExpanded, collapseAll }">
            <SelectedItems
                :scope-key="history.id"
                :get-item-key="(item) => item.type_id"
                v-slot="{
                    selectedItems,
                    showSelection,
                    setShowSelection,
                    selectItems,
                    isSelected,
                    setSelected,
                    resetSelection,
                }">
                <Layout>
                    <template v-slot:navigation>
                        <slot name="navigation" :history="history" />
                        <HistoryFilters class="content-operations-filters mx-3" :params.sync="params" />
                    </template>

                    <template v-slot:details>
                        <HistoryDetails :history="history" v-on="$listeners" />
                    </template>

                    <template v-slot:messages>
                        <HistoryMessages class="m-2" :history="history" />
                    </template>

                    <template v-slot:listcontrols>
                        <HistoryOperations
                            :history="history"
                            :params.sync="params"
                            :content-selection="selectedItems"
                            :show-selection="showSelection"
                            :expanded-count="expandedCount"
                            :has-matches="hasMatches(payload)"
                            @update:content-selection="selectItems"
                            @update:show-selection="setShowSelection"
                            @reset-selection="resetSelection"
                            @hide-selection="onHideSelection"
                            @select-all="selectItems(payload)"
                            @collapse-all="collapseAll" />
                    </template>

                    <template v-slot:listing>
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
                        <Listing v-else :items="payload" @scroll="onScroll">
                            <template v-slot:history-item="{ item }">
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
                    </template>

                    <template v-slot:modals>
                        <ToolHelpModal />
                    </template>
                </Layout>
            </SelectedItems>
        </ExpandedItems>
    </HistoryItemsProvider>
</template>

<script>
import Vue from "vue";
import { HistoryItemsProvider } from "components/providers/storeProviders";
import LoadingSpan from "components/LoadingSpan";
import ContentItem from "components/History/Content/ContentItem";
import { History } from "components/History/model";
import { deleteContent, updateContentFields } from "components/History/model/queries";
import ExpandedItems from "components/History/Content/ExpandedItems";
import SelectedItems from "components/History/Content/SelectedItems";
import Layout from "components/History/Layout/Layout";
import Listing from "components/History/Layout/Listing";
import ToolHelpModal from "components/History/Modals/ToolHelpModal";
import HistoryOperations from "./HistoryOperations";
import HistoryDetails from "./HistoryDetails";
import HistoryEmpty from "./HistoryEmpty";
import HistoryFilters from "./HistoryFilters";
import HistoryMessages from "./HistoryMessages";

export default {
    components: {
        LoadingSpan,
        Layout,
        Listing,
        ContentItem,
        HistoryMessages,
        HistoryDetails,
        HistoryEmpty,
        HistoryFilters,
        HistoryItemsProvider,
        HistoryOperations,
        ToolHelpModal,
        ExpandedItems,
        SelectedItems,
    },
    props: {
        history: { type: History, required: true },
    },
    data() {
        return {
            invisible: {},
            offset: 0,
            params: {
                filterText: "",
                showDeleted: false,
                showHidden: false,
            },
        };
    },
    watch: {
        queryKey() {
            this.invisible = {};
            this.offset = 0;
        },
    },
    computed: {
        historyId() {
            return this.history.id;
        },
        queryKey() {
            return `${this.historyId}-${this.params.showDeleted}-${this.params.showHidden}-${this.params.filterText}`;
        },
        queryDefault() {
            return !this.params.showDeleted && !this.params.showHidden && !this.params.filterText;
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
