<!-- When a dataset collection is being viewed, this panel shows the contents of that collection -->

<template>
    <UrlDataProvider v-if="dsc" :url="getUrl(selectedCollection)" v-slot="{ result: payload }">
        <ExpandedItems
            :scope-key="selectedCollection.id"
            :get-item-key="(item) => item.element_index"
            v-slot="{ isExpanded, setExpanded }">
            <Layout class="dataset-collection-panel">
                <template v-slot:globalnav>
                    <TopNav :history="history" :selected-collections="selectedCollections" v-on="$listeners" />
                </template>

                <template v-slot:localnav>
                    <!-- Empty -->
                    <div />
                </template>

                <template v-slot:listcontrols>
                    <Operations :collection="selectedCollection" :is-root="isRoot" />
                </template>

                <template v-slot:details>
                    <Details :dsc="dsc" :writable="writable" @update:dsc="updateDsc(dsc, $event)" />
                </template>

                <template v-slot:listing>
                    <HistoryListing
                        item-key="element_index"
                        :page-size="pageSize"
                        :payload="payload"
                        @scroll="onScroll">
                        <template v-slot:history-item="{ item, index }">
                            <ContentItem
                                :item="item"
                                :id="item.element_index"
                                :name="item.element_identifier"
                                :expandable="item.element_type == 'hda'"
                                :state="item.object.state"
                                :expanded="isExpanded(item)"
                                :writeable="false"
                                @update:expanded="setExpanded(item, $event)"
                                @drilldown="$emit('viewCollection', item)" />
                        </template>
                    </HistoryListing>
                </template>
            </Layout>
        </ExpandedItems>
    </UrlDataProvider>
</template>

<script>
import { DatasetCollection } from "../model";
import { History } from "../model";
import { updateContentFields } from "../model/queries";
import ExpandedItems from "../ExpandedItems";
import Layout from "../Layout";
import TopNav from "./TopNav";
import Operations from "./Operations";
import Details from "./Details";
import ContentItem from "../ContentItem/ContentItem";
import HistoryListing from "components/History/HistoryListing";
import { UrlDataProvider } from "components/providers/UrlDataProvider";

export default {
    components: {
        UrlDataProvider,
        Layout,
        TopNav,
        Details,
        ContentItem,
        ExpandedItems,
        Operations,
        HistoryListing,
    },
    props: {
        history: { type: History, required: true },
        selectedCollections: { type: Array, required: true },
    },
    data() {
        return {
            pageSize: 50,
        };
    },
    created() {
        this.dsc = new DatasetCollection(this.selectedCollection);
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
    },
    methods: {
        getUrl(dsc) {
            return dsc.contents_url.substring(1);
        },
        // change the data of the root collection, anything past the root
        // collection is part of the dataset collection, which i believe is supposed to
        // be immutable, so only edit name, tags, blah of top-level selected collection,
        async updateDsc(collection, fields) {
            if (this.writable) {
                await updateContentFields(collection, fields);
            }
        },
        onScroll(newHid) {
            this.maxHid = newHid;
        },
    },
};
</script>
