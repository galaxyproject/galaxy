<template>
    <HistoryContentProvider
        :parent="history"
        :params="params"
        :disable-poll="false"
        :debug="false"
        :debounce-period="500"
        v-slot="{ loading, payload, manualReload, setScrollPos }">
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
                            :expanded-count="expandedCount"
                            @collapseAllContent="collapseAll" />
                    </template>

                    <template v-slot:listing>
                        <HistoryEmpty v-if="history.empty" class="m-2" />
                        <HistoryEmpty v-else-if="payload && payload.noResults" message="No Results." class="m-2" />
                        <Scroller
                            v-else-if="payload"
                            :class="{ loadingBackground: loading }"
                            key-field="hid"
                            v-bind="payload"
                            :debug="false"
                            @scroll="setScrollPos">
                            <template v-slot="{ item, index, rowKey }">
                                <HistoryContentItem
                                    :item="item"
                                    :index="index"
                                    :row-key="rowKey"
                                    :show-selection="showSelection"
                                    :expanded="isExpanded(item)"
                                    @update:expanded="setExpanded(item, $event)"
                                    :selected="isSelected(item)"
                                    @update:selected="setSelected(item, $event)"
                                    @viewCollection="$emit('viewCollection', item)"
                                    :data-hid="item.hid"
                                    :data-index="index"
                                    :data-row-key="rowKey" />
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
import { History } from "./model";
import { SearchParams } from "components/providers/History/SearchParams";
import { HistoryContentProvider } from "components/providers/History/";
import ExpandedItems from "./ExpandedItems";
import SelectedItems from "./SelectedItems";
import Layout from "./Layout";
import HistoryMessages from "./HistoryMessages";
import HistoryDetails from "./HistoryDetails";
import HistoryEmpty from "./HistoryEmpty";
import ContentOperations from "./ContentOperations";
import ToolHelpModal from "./ToolHelpModal";
import Scroller from "./Scroller";
import { HistoryContentItem } from "./ContentItem";
import { reportPayload } from "components/providers/History/ContentProvider/helpers";
import HistoryMenu from "./HistoryMenu";

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
        HistoryMenu,
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
