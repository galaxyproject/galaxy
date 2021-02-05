<template>
    <HistoryContentProvider
        :parent="history"
        v-slot="{
            loading,
            params,
            payload: { contents = [], startKey = null, topRows = 0, bottomRows = 0, totalMatches = 0 },
            handlers: { updateParams, manualReload, setScrollPos },
        }"
    >
        <ExpandedItems
            :scope-key="history.id"
            :get-item-key="(item) => item.type_id"
            v-slot="{ isExpanded, setExpanded }"
        >
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
                }"
            >
                <Layout>
                    <template v-slot:nav>
                        <slot name="nav"></slot>
                    </template>

                    <template v-slot:details>
                        <HistoryDetails class="history-details" :history="history" v-on="$listeners" />
                    </template>

                    <template v-slot:messages>
                        <HistoryMessages class="history-messages m-2" :history="history" />
                    </template>

                    <template v-slot:listcontrols>
                        <ContentOperations
                            v-if="!history.empty"
                            :history="history"
                            :total-matches="totalMatches"
                            :loading="loading"
                            :params="params"
                            @update:params="updateParams"
                            :content-selection="selectedItems"
                            @update:content-selection="selectItems"
                            :show-selection="showSelection"
                            @update:show-selection="setShowSelection"
                            @resetSelection="resetSelection"
                            @selectAllContent="selectItems(contents)"
                            @manualReload="manualReload"
                        />
                    </template>

                    <template v-slot:listing>
                        <HistoryEmpty v-if="history.empty" class="m-2" />

                        <VirtualScroller
                            v-else
                            :class="{ loadingBackground: loading }"
                            key-field="hid"
                            :item-height="36"
                            :items="contents"
                            :scroll-to="startKey"
                            :top-placeholders="topRows"
                            :bottom-placeholders="bottomRows"
                            @scroll="setScrollPos"
                        >
                            <template v-slot="{ item, index }">
                                <HistoryContentItem
                                    :item="item"
                                    :index="index"
                                    :show-selection="showSelection"
                                    :expanded="isExpanded(item)"
                                    @update:expanded="setExpanded(item, $event)"
                                    :selected="isSelected(item)"
                                    @update:selected="setSelected(item, $event)"
                                    @viewCollection="$emit('viewCollection', item)"
                                />
                            </template>
                        </VirtualScroller>
                    </template>

                    <template v-slot:modals>
                        <ToolHelpModal />
                    </template>
                </Layout>
            </SelectedItems>
        </ExpandedItems>
    </HistoryContentProvider>
</template>

<script>
import { History } from "./model";
import { HistoryContentProvider, ExpandedItems, SelectedItems } from "./providers";
import Layout from "./Layout";
import HistoryMessages from "./HistoryMessages";
import HistoryDetails from "./HistoryDetails";
import HistoryEmpty from "./HistoryEmpty";
import ContentOperations from "./ContentOperations";
import ToolHelpModal from "./ToolHelpModal";
import VirtualScroller from "../VirtualScroller";
import { HistoryContentItem } from "./ContentItem";

export default {
    components: {
        HistoryContentProvider,
        Layout,
        HistoryMessages,
        HistoryDetails,
        HistoryEmpty,
        ContentOperations,
        ToolHelpModal,
        VirtualScroller,
        HistoryContentItem,
        ExpandedItems,
        SelectedItems,
    },
    props: {
        history: { type: History, required: true },
    },
    computed: {
        historyId() {
            return this.history.id;
        },
    },
};
</script>
