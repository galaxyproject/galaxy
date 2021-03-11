<template>
    <HistoryContentProvider :parent="history" :params="params" v-slot="{ loading, payload, setScrollPos }">
        <ExpandedContent :scope="historyId" :get-key="pluckType" v-slot="expanded">
            <SelectedContent :scope="historyId" :get-key="pluckType" v-slot="selected">
                <Layout>
                    <template v-slot:nav>
                        <!-- pass-through slot -->
                        <slot name="nav"></slot>
                    </template>

                    <template v-slot:details>
                        <HistoryDetails class="history-details" :history="history" v-on="$listeners" />
                    </template>

                    <template v-slot:messages>
                        <HistoryMessages class="history-messages m-2" :history="history" />
                    </template>

                    <template v-slot:listcontrols>
                        <BulkOperations
                            :history="history"
                            :filters="params"
                            :content-selection="selected.items"
                            :item-mode="useItemSelection"
                            v-slot="{ operations, execute }"
                        >
                            <ContentOperations
                                v-frag
                                v-if="!history.empty"
                                :history="history"
                                :filters.sync="params"
                                :query-matches="payload.totalMatches"
                                :content-selection="selected.items"
                                :use-item-selection.sync="useItemSelection"
                                :operations="operations"
                                @execute="execute"
                                @collapseAllContent="expanded.reset"
                                @resetSelection="selected.reset"
                            />
                        </BulkOperations>
                    </template>

                    <template v-slot:listing>
                        <HistoryEmpty v-if="history.empty" class="m-2" />
                        <Scroller
                            v-else
                            :class="{ loadingBackground: loading }"
                            key-field="hid"
                            :item-height="36"
                            :items="payload.contents"
                            :top-placeholders="payload.topRows"
                            :bottom-placeholders="payload.bottomRows"
                            :scroll-to="payload.startKey"
                            @scroll="setScrollPos"
                        >
                            <template v-slot="{ item, index }">
                                <HistoryContentItem
                                    :item="item"
                                    :index="index"
                                    :show-selection="useItemSelection"
                                    :expanded="expanded.has(item)"
                                    @update:expanded="expanded.toggle(item, $event)"
                                    :selected="selected.has(item)"
                                    @update:selected="selected.toggle(item, $event)"
                                    @viewCollection="$emit('viewCollection', item)"
                                />
                            </template>
                        </Scroller>
                    </template>

                    <template v-slot:modals>
                        <ToolHelpModal />
                    </template>
                </Layout>
            </SelectedContent>
        </ExpandedContent>
    </HistoryContentProvider>
</template>

<script>
import { default as ExpandedContent, default as SelectedContent } from "components/providers/ToggleList";
import { History, SearchParams } from "./model";
import { HistoryContentProvider, BulkOperations } from "./providers";
import Layout from "./Layout";
import HistoryDetails from "./HistoryDetails";
import HistoryMessages from "./HistoryMessages";
import ContentOperations from "./ContentOperations";
import HistoryEmpty from "./HistoryEmpty";
import Scroller from "./Scroller";
import { HistoryContentItem } from "./ContentItem";
import ToolHelpModal from "./ToolHelpModal";

export default {
    components: {
        HistoryContentProvider,
        ExpandedContent,
        SelectedContent,
        Layout,
        HistoryDetails,
        HistoryMessages,
        ContentOperations,
        HistoryEmpty,
        Scroller,
        HistoryContentItem,
        ToolHelpModal,
        BulkOperations,
    },
    props: {
        history: { type: History, required: true },
    },
    data() {
        return {
            params: new SearchParams(),
            useItemSelection: false,
        };
    },
    computed: {
        // selects type_id for list management
        pluckType() {
            return (o) => o.type_id;
        },
        historyId() {
            return this.history.id;
        },
    },
};
</script>
