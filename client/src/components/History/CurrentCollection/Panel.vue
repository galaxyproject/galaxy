<!-- When a dataset collection is being viewed, this panel shows the contents of that collection -->

<template>
    <DscProvider :is-root="isRoot" :debounce-period="500" :collection="selectedCollection" v-slot="{ dsc }">
        <UrlDataProvider v-if="dsc" :url="dsc.url" :auto-refresh="false" v-slot="{ loading, result: payload }">
            <ExpandedItems
                :scope-key="selectedCollection.id"
                :get-item-key="(item) => item.type_id"
                v-slot="{ isExpanded, setExpanded }">
                <Layout class="dataset-collection-panel">
                    <template v-slot:globalnav>
                        {{ payload }}
                        <TopNav :history="history" :selected-collections="selectedCollections" v-on="$listeners" />
                    </template>

                    <template v-slot:localnav>
                        <!-- Empty -->
                        <div />
                    </template>

                    <template v-slot:listcontrols>
                        <CollectionOperations :collection="selectedCollection" :is-root="isRoot" />
                    </template>

                    <template v-slot:details>
                        <Details :dsc="dsc" :writable="writable" @update:dsc="updateDsc(dsc, $event)" />
                    </template>

                    <template v-slot:listing>
                        <HistoryListing
                            :query-key="dsc.id"
                            :page-size="pageSize"
                            :payload="payload"
                            @scroll="onScroll">
                            <template v-slot:history-item="{ item }">
                                <CollectionContentItem
                                    :item="item"
                                    :expanded="isExpanded(item)"
                                    :writable="false"
                                    :selectable="false"
                                    @update:expanded="setExpanded(item, $event)"
                                    @viewCollection="$emit('viewCollection', item)" />
                            </template>
                        </HistoryListing>
                    </template>
                </Layout>
            </ExpandedItems>
        </UrlDataProvider>
    </DscProvider>
</template>

<script>
import { History } from "../model";
import { updateContentFields } from "../model/queries";

import { DscProvider, CollectionContentProvider } from "components/providers/History";
import ExpandedItems from "../ExpandedItems";
import Layout from "../Layout";
import TopNav from "./TopNav";
import CollectionOperations from "./CollectionOperations.vue";
import Details from "./Details";
import Scroller from "../Scroller";
import { CollectionContentItem } from "../ContentItem";
import HistoryListing from "components/History/HistoryListing";
import { reportPayload } from "components/providers/History/ContentProvider/helpers";
import { UrlDataProvider } from "components/providers/UrlDataProvider";

export default {
    filters: {
        reportPayload,
    },
    components: {
        UrlDataProvider,
        DscProvider,
        CollectionContentProvider,
        Layout,
        TopNav,
        Details,
        Scroller,
        CollectionContentItem,
        ExpandedItems,
        CollectionOperations,
        HistoryListing,
    },
    props: {
        history: { type: History, required: true },
        selectedCollections: { type: Array, required: true },
    },
    data() {
        return {
            pageSize: 50,
        }
    },
    computed: {
        selectedCollection() {
            const arr = this.selectedCollections;
            const selected = arr[arr.length - 1];
            return selected;
        },
        isRoot() {
            return this.selectedCollection == this.rootCollection;
        },
        writable() {
            return this.isRoot;
        },
        rootCollection() {
            return this.selectedCollections[0];
        },
        downloadCollectionUrl() {
            let url = "";
            if (this.rootCollection) {
                url = `${this.rootCollection.url}/download`;
            }
            return url;
        },
        dataUrl() {
            return `api/histories/${this.historyId}/contents/before/${this.maxHid + this.maxNew}/${this.pageSize}?${
                this.queryString
            }`;
        },
    },
    methods: {
        // change the data of the root collection, anything past the root
        // collection is part of the dataset collection, which i believe is supposed to
        // be immutable, so only edit name, tags, blah of top-level selected collection,
        async updateDsc(collection, fields) {
            if (this.writable) {
                const ajaxResult = await updateContentFields(collection, fields);
            }
        },
        onScroll(newHid) {
            this.maxHid = newHid;
        },
    },
};
</script>
