<template>
    <HistoryContentProvider
        :parent="history"
        :params="params"
        :disable-poll="false"
        :debug="false"
        :debounce-period="500"
        v-slot="{ loading, payload, manualReload, setScrollPos }"
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
                            :total-matches="payload.totalMatches"
                            :loading="loading"
                            :params.sync="params"
                            :content-selection="selectedItems"
                            @update:content-selection="selectItems"
                            :show-selection="showSelection"
                            @update:show-selection="setShowSelection"
                            @resetSelection="resetSelection"
                            @selectAllContent="selectItems(payload.contents)"
                            @manualReload="manualReload"
                        />
                    </template>

                    <template v-slot:listing>
                        <HistoryEmpty v-if="history.empty && payload.contents.length == 0" class="m-2" />
                        <Scroller
                            v-else
                            :class="{ loadingBackground: loading }"
                            key-field="hid"
                            v-bind="payload"
                            :debug="false"
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
                        </Scroller>
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
import { History, SearchParams } from "./model";
import { HistoryContentProvider, ExpandedItems, SelectedItems } from "./providers";
import Layout from "./Layout";
import HistoryMessages from "./HistoryMessages";
import HistoryDetails from "./HistoryDetails";
import HistoryEmpty from "./HistoryEmpty";
import ContentOperations from "./ContentOperations";
import ToolHelpModal from "./ToolHelpModal";
import Scroller from "./Scroller";
import { HistoryContentItem } from "./ContentItem";
import { reportPayload } from "./providers/ContentProvider/helpers";

export default {
    filters: {
        reportPayload,
    },
    components: {
        HistoryContentProvider,
        Layout,
        HistoryMessages,
        HistoryDetails,
        HistoryEmpty,
        ContentOperations,
        ToolHelpModal,
        Scroller,
        HistoryContentItem,
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
        };
    },
    computed: {
        historyId() {
            return this.history.id;
        },
    },
};
</script>
