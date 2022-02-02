<template>
    <UrlDataProvider :url="dataUrl" :auto-refresh="true" v-slot="{ loading, result: payload }">
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
                    <template v-slot:globalNav>
                        <slot name="globalNav" :history="history"></slot>
                    </template>

                    <template v-slot:localNav>
                        <HistoryMenu :history="history" v-on="$listeners" />
                    </template>

                    <template v-slot:details>
                        <HistoryDetails :history="history" v-on="$listeners" />
                    </template>

                    <template v-slot:messages>
                        <HistoryMessages class="m-2" :history="history" />
                    </template>

                    <template v-slot:listcontrols>
                        <ContentOperations
                            :history="history"
                            :total-matches="100"
                            :loading="loading"
                            :params.sync="params"
                            :content-selection="selectedItems"
                            @update:content-selection="selectItems"
                            :show-selection="showSelection"
                            @update:show-selection="setShowSelection"
                            @resetSelection="resetSelection"
                            @selectAllContent="selectItems(payload.contents)"
                            :expanded-count="expandedCount"
                            @collapseAllContent="collapseAll" />
                    </template>

                    <template v-slot:listing>
                        <HistoryEmpty v-if="history.empty" class="m-2" />
                        <b-alert v-else-if="loading" class="m-2" variant="info" show>
                            <LoadingSpan message="Loading History" />
                        </b-alert>
                        <HistoryListing
                            v-else
                            @scroll="onScroll"
                            :payload="payload"
                            :show-selection="showSelection"
                            :is-expanded="isExpanded"
                            :set-expanded="setExpanded"
                            :is-selected="isSelected"
                            :set-selected="setSelected"
                            :loading="loading"
                            :page-size="params.pageSize"
                            :history-id="history.id" />
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
import { History } from "./model";
import LoadingSpan from "components/LoadingSpan";
import { SearchParams } from "components/providers/History/SearchParams";
import { UrlDataProvider } from "components/providers/UrlDataProvider";
import ExpandedItems from "./ExpandedItems";
import SelectedItems from "./SelectedItems";
import Layout from "./Layout";
import HistoryMessages from "./HistoryMessages";
import HistoryDetails from "./HistoryDetails";
import HistoryEmpty from "./HistoryEmpty";
import ContentOperations from "./ContentOperations";
import ToolHelpModal from "./ToolHelpModal";
import { reportPayload } from "components/providers/History/ContentProvider/helpers";
import HistoryMenu from "./HistoryMenu";
import HistoryListing from "./HistoryListing";

export default {
    filters: {
        reportPayload,
    },
    components: {
        LoadingSpan,
        UrlDataProvider,
        Layout,
        HistoryMessages,
        HistoryDetails,
        HistoryEmpty,
        HistoryMenu,
        HistoryListing,
        ContentOperations,
        ToolHelpModal,
        ExpandedItems,
        SelectedItems,
    },
    props: {
        history: { type: History, required: true },
    },
    data() {
        return {
            params: new SearchParams(),
            useItemSelection: false,
            maxHid: this.history.hid_counter,
        };
    },
    computed: {
        historyId() {
            return this.history.id;
        },
        dataUrl() {
            return `api/histories/${this.historyId}/contents/before/${this.maxHid}/40`;
        },
    },
    methods: {
        onScroll(newHid) {
            this.maxHid = newHid;
        },
    },
};
</script>
