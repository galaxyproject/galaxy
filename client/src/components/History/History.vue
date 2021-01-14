<template>
    <HistoryContentProvider
        :parent="history"
        v-slot="{
            loading,
            scrolling,
            params,
            pageSize,
            payload: {
                contents = [],
                startKey = null,
                topRows = 0,
                bottomRows = 0,
                totalMatches = 0,
            },
            updateParams,
            setScrollPos,
            manualReload,
        }"
    >
        <Layout>
            <!-- optional top-nav slot, for right-side history panel -->
            <template v-slot:nav>
                <slot name="nav"></slot>
            </template>

            <template v-slot:details>
                <HistoryDetails class="history-details" :history="history" />
            </template>

            <template v-slot:messages>
                <HistoryMessages class="history-messages m-2" :history="history" />
                <HistoryEmpty v-if="history.empty" class="m-2" />
            </template>

            <template v-slot:listcontrols>
                <ContentOperations
                    :history="history"
                    :params="params"
                    @update:params="updateParams"
                    :total-matches="totalMatches"
                    :loading="loading"
                    :content-selection.sync="listState.selected"
                    :show-selection.sync="listState.showSelection"
                    @resetSelection="resetSelection"
                    @selectAllContent="selectItems(contents)"
                    @manualReload="manualReload"
                />
            </template>

            <template v-slot:listing>
                <VirtualScroller
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
                        <HistoryContentItem :item="item" :index="index" v-on="$listeners" />
                    </template>
                </VirtualScroller>
            </template>

            <template v-slot:modals>
                <ToolHelpModal />
            </template>
        </Layout>
    </HistoryContentProvider>
</template>

<script>
import { History } from "./model";
import { HistoryContentProvider } from "./providers";
import Layout from "./Layout";
import HistoryMessages from "./HistoryMessages";
import HistoryDetails from "./HistoryDetails";
import HistoryEmpty from "./HistoryEmpty";
import ContentOperations from "./ContentOperations";
import ToolHelpModal from "./ToolHelpModal";
import ListMixin from "./ListMixin";
import VirtualScroller from "../VirtualScroller";
import { HistoryContentItem } from "./ContentItem";

export default {
    mixins: [ListMixin],
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
    },
    props: {
        history: { type: History, required: true },
    },
    computed: {
        historyId() {
            return this.history.id;
        },
    },
    watch: {
        historyId(newId, oldId) {
            if (newId && newId !== oldId) {
                this.resetSelection();
                this.resetExpanded();
            }
        },
    },
};
</script>
