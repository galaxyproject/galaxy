<template>
    <UrlDataProvider :key="history.id" :url="dataUrl" auto-refresh v-slot="{ loading, result: payload }">
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
                        <HistoryMenu :history="history" v-on="$listeners" />
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
                            @hide-selection="onhideSelection"
                            @select-all="selectItems(payload)"
                            @collapse-all="collapseAll" />
                    </template>

                    <template v-slot:listing>
                        <HistoryEmpty v-if="payload && payload.length == 0" class="m-2" />
                        <b-alert v-else-if="loading" class="m-2" variant="info" show>
                            <LoadingSpan message="Loading History" />
                        </b-alert>
                        <Listing
                            v-else
                            reversed
                            :query-key="queryKey"
                            :page-size="pageSize"
                            :payload="payload"
                            @scroll="onScroll">
                            <template v-slot:history-item="{ item }">
                                <ContentItem
                                    v-if="!hideSelection[item.hid]"
                                    :item="item"
                                    :id="item.hid"
                                    :name="item.name"
                                    :state="getState(item)"
                                    :expanded="isExpanded(item)"
                                    :expandable="item.history_content_type == 'dataset'"
                                    :selected="isSelected(item)"
                                    :selectable="showSelection"
                                    @update:expanded="setExpanded(item, $event)"
                                    @update:selected="setSelected(item, $event)"
                                    @drilldown="$emit('viewCollection', item)"
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
    </UrlDataProvider>
</template>

<script>
import { UrlDataProvider } from "components/providers/UrlDataProvider";
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
import HistoryMenu from "./HistoryMenu";
import HistoryMessages from "./HistoryMessages";

export default {
    components: {
        LoadingSpan,
        UrlDataProvider,
        Layout,
        Listing,
        ContentItem,
        HistoryMessages,
        HistoryDetails,
        HistoryEmpty,
        HistoryMenu,
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
            hideSelection: {},
            topIndex: 0,
            pageSize: 2000,
            params: {},
        };
    },
    watch: {
        queryKey() {
            this.hideSelection = {};
            this.topIndex = 0;
        },
    },
    computed: {
        dataUrl() {
            return `api/histories/${this.historyId}/contents?v=dev&order=hid&offset=${this.topIndex}&${this.queryString}`;
        },
        historyId() {
            return this.history.id;
        },
        queryKey() {
            return `${this.history.id}&${this.queryString}`;
        },
        queryString() {
            const deleted = this.params.showDeleted ? "True" : "False";
            const visible = this.params.showHidden ? "False" : "True";
            return `q=deleted&q=visible&qv=${deleted}&qv=${visible}`;
        },
    },
    methods: {
        getState(item) {
            if (item.job_state_summary) {
                for (const key of ["error", "failed", "paused", "upload", "running"]) {
                    if (item.job_state_summary[key] > 0) {
                        return key;
                    }
                }
                return "ok";
            } else {
                return item.state || item.populated_state;
            }
        },
        hasMatches(payload) {
            return !!payload && payload.length > 0;
        },
        onScroll(newHid) {
            this.topIndex = newHid;
        },
        onhideSelection(selectedItems) {
            selectedItems.forEach((item) => {
                this.hideSelection[item.hid] = true;
            });
        },
        onDelete(item) {
            this.hideSelection[item.hid] = true;
            deleteContent(item);
        },
        onUndelete(item) {
            this.hideSelection[item.hid] = true;
            updateContentFields(item, { deleted: false });
        },
        onUnhide(item) {
            this.hideSelection[item.hid] = true;
            updateContentFields(item, { visible: true });
        },
    },
};
</script>
