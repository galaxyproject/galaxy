<!-- When a dataset collection is being viewed, this panel shows the contents of that collection -->

<template>
    <UrlDataProvider v-if="dsc" :key="dsc.id" :url="url" v-slot="{ result: payload }">
        <ExpandedItems :scope-key="dsc.id" :get-item-key="(item) => item.id" v-slot="{ isExpanded, setExpanded }">
            <Layout class="dataset-collection-panel">
                <template v-slot:navigation>
                    <CollectionNavigation
                        :history="history"
                        :selected-collections="selectedCollections"
                        v-on="$listeners" />
                </template>

                <template v-slot:listcontrols>
                    <CollectionOperations :collection="dsc" :is-root="isRoot" />
                </template>

                <template v-slot:details>
                    <CollectionDetails :dsc="dsc" :writeable="writeable" @update:dsc="updateDsc(dsc, $event)" />
                </template>

                <template v-slot:listing>
                    <Listing item-key="element_index" :payload="payload" :limit="limit" @scroll="onScroll">
                        <template v-slot:history-item="{ item }">
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
            limit: 500,
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
            return this.dsc.contents_url.substring(1);
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
