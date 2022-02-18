<!-- When a dataset collection is being viewed, this panel shows the contents of that collection -->

<template>
    <UrlDataProvider v-if="dsc" :key="dsc.id" :url="url" v-slot="{ result: payload }">
        <ExpandedItems
            :scope-key="dsc.id"
            :get-item-key="(item) => item.element_index"
            v-slot="{ isExpanded, setExpanded }">
            <Layout class="dataset-collection-panel">
                <template v-slot:navigation>
                    <Navigation :history="history" :selected-collections="selectedCollections" v-on="$listeners" />
                </template>

                <template v-slot:listcontrols>
                    <Operations :collection="dsc" :is-root="isRoot" />
                </template>

                <template v-slot:details>
                    <Details :dsc="dsc" :writeable="writeable" @update:dsc="updateDsc(dsc, $event)" />
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
                                :state="item.object ? item.object.state : item.populated_state"
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
import { DatasetCollection, History } from "components/History/model";
import { updateContentFields } from "components/History/model/queries";
import ExpandedItems from "../ExpandedItems";
import Layout from "../Layout";
import Navigation from "./Navigation";
import Operations from "./Operations";
import Details from "./Details";
import ContentItem from "../ContentItem/ContentItem";
import HistoryListing from "components/History/HistoryListing";
import { UrlDataProvider } from "components/providers/UrlDataProvider";

export default {
    components: {
        UrlDataProvider,
        Layout,
        Navigation,
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
    computed: {
        dsc() {
            const arr = this.selectedCollections;
            return arr[arr.length - 1];
        },
        isRoot() {
            return this.dsc == this.rootCollection;
        },
        writeable() {
            return this.isRoot;
        },
        rootCollection() {
            return this.selectedCollections[0];
        },
        url() {
            return `api/dataset_collections/${this.rootCollection.id}/contents/${this.dsc.id}`;
        },
    },
    methods: {
        // change the data of the root collection, anything past the root
        // collection is part of the dataset collection, which i believe is supposed to
        // be immutable, so only edit name, tags etc of top-level selected collection.
        async updateDsc(collection, fields) {
            if (this.writeable) {
                await updateContentFields(collection, fields);
            }
        },
        onScroll(newHid) {
            this.maxHid = newHid;
        },
    },
};
</script>
