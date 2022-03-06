<!-- When a dataset collection is being viewed, this panel shows the contents of that collection -->

<template>
    <UrlDataProvider v-if="dsc" :key="dsc.id" :url="url" auto-refresh v-slot="{ result: payload }">
        <ExpandedItems :scope-key="dsc.id" :get-item-key="(item) => item.id" v-slot="{ isExpanded, setExpanded }">
            <Layout class="dataset-collection-panel">
                <template v-slot:navigation>
                    <CollectionNavigation
                        :history="history"
                        :selected-collections="selectedCollections"
                        v-on="$listeners" />
                </template>

                <template v-slot:listcontrols>
                    <CollectionOperations v-if="isRoot" :dsc="dsc" />
                </template>

                <template v-slot:details>
                    <CollectionDetails :dsc="dsc" :writeable="isRoot" @update:dsc="updateDsc(dsc, $event)" />
                </template>

                <template v-slot:listing>
                    <Listing item-key="element_index" :payload="payload" :limit="limit" @scroll="onScroll">
                        <template v-slot:history-item="{ item }">
                            <ContentItem
                                :item="item"
                                :id="item.element_index"
                                :name="item.element_identifier"
                                :is-dataset="item.element_type == 'hda'"
                                :state="item.object ? item.object.state : item.populated_state"
                                :expand-dataset="isExpanded(item)"
                                :is-history-item="false"
                                @update:expand-dataset="setExpanded(item, $event)"
                                @view-collection="$emit('view-collection', item)" />
                        </template>
                    </Listing>
                </template>
            </Layout>
        </ExpandedItems>
    </UrlDataProvider>
</template>

<script>
import { UrlDataProvider } from "components/providers/UrlDataProvider";
import { History } from "components/History/model";
import { updateContentFields } from "components/History/model/queries";
import ContentItem from "components/History/Content/ContentItem";
import ExpandedItems from "components/History/Content/ExpandedItems";
import Listing from "components/History/Layout/Listing";
import Layout from "components/History/Layout/Layout";
import CollectionNavigation from "./CollectionNavigation";
import CollectionOperations from "./CollectionOperations";
import CollectionDetails from "./CollectionDetails";

export default {
    components: {
        CollectionDetails,
        CollectionNavigation,
        CollectionOperations,
        ContentItem,
        ExpandedItems,
        Layout,
        Listing,
        UrlDataProvider,
    },
    props: {
        history: { type: History, required: true },
        selectedCollections: { type: Array, required: true },
    },
    data() {
        return {
            offset: 0,
            limit: 100,
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
        rootCollection() {
            return this.selectedCollections[0];
        },
        url() {
            const source = this.dsc.object || this.dsc;
            const contentsUrl = source.contents_url.substring(1);
            return `${contentsUrl}?offset=${this.offset}&limit=${this.limit}`;
        },
    },
    methods: {
        updateDsc(collection, fields) {
            updateContentFields(collection, fields).then((response) => {
                Object.keys(response).forEach((key) => {
                    collection[key] = response[key];
                });
            });
        },
        onScroll(offset) {
            this.offset = offset;
        },
    },
};
</script>
