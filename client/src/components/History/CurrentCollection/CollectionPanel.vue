<!-- When a dataset collection is being viewed, this panel shows the contents of that collection -->

<template>
    <CollectionElementsProvider
        v-if="dsc"
        :key="dsc.id"
        :id="dsc.id"
        :contents-url="contentsUrl"
        :offset="offset"
        v-slot="{ loading, result: payload }">
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
                    <Listing :items="payload" :loading="loading" @scroll="onScroll">
                        <template v-slot:history-item="{ item }">
                            <ContentItem
                                :item="item.object"
                                :id="item.element_index"
                                :name="item.element_identifier"
                                :is-dataset="item.element_type == 'hda'"
                                :expand-dataset="isExpanded(item)"
                                :is-history-item="false"
                                @update:expand-dataset="setExpanded(item, $event)"
                                @view-collection="onViewSubCollection" />
                        </template>
                    </Listing>
                </template>
            </Layout>
        </ExpandedItems>
    </CollectionElementsProvider>
</template>

<script>
import { CollectionElementsProvider } from "components/providers/storeProviders";
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
        CollectionElementsProvider,
        CollectionNavigation,
        CollectionOperations,
        ContentItem,
        ExpandedItems,
        Layout,
        Listing,
    },
    props: {
        history: { type: History, required: true },
        selectedCollections: { type: Array, required: true },
    },
    data() {
        return {
            offset: 0,
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
        contentsUrl() {
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
        /**
         * Passes a sub-collection i.e a collection element object containing another collection, into
         * a populated object for drilldown without the need for a separate data request. This object
         * is used for breadcrumbs in the navigation component and to render the collection details and
         * description at the top of the collection panel. Details include the collection name, the
         * collection type, and the element count.
         */
        onViewSubCollection(itemObject, elementIdentifer) {
            const collectionObject = {
                name: elementIdentifer,
                ...itemObject,
            };
            this.$emit("view-collection", collectionObject);
        },
    },
};
</script>
