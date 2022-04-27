<!-- When a dataset collection is being viewed, this panel shows the contents of that collection -->

<template>
    <CollectionElementsProvider
        v-if="dsc"
        :id="dsc.id"
        :key="dsc.id"
        v-slot="{ loading, result: payload }"
        :contents-url="contentsUrl"
        :offset="offset">
        <ExpandedItems v-slot="{ isExpanded, setExpanded }" :scope-key="dsc.id" :get-item-key="(item) => item.id">
            <section class="dataset-collection-panel d-flex flex-column">
                <section>
                    <CollectionNavigation
                        :history="history"
                        :selected-collections="selectedCollections"
                        v-on="$listeners" />
                    <CollectionDetails :dsc="dsc" :writeable="isRoot" @update:dsc="updateDsc(dsc, $event)" />
                    <CollectionOperations v-if="isRoot" :dsc="dsc" />
                </section>
                <section class="position-relative flex-grow-1 scroller">
                    <div>
                        <Listing :items="payload" :loading="loading" @scroll="onScroll">
                            <template v-slot:item="{ item }">
                                <ContentItem
                                    :id="item.element_index"
                                    :item="item.object"
                                    :name="item.element_identifier"
                                    :expand-dataset="isExpanded(item)"
                                    :is-dataset="item.element_type == 'hda'"
                                    :is-history-item="false"
                                    @update:expand-dataset="setExpanded(item, $event)"
                                    @view-collection="onViewSubCollection" />
                            </template>
                        </Listing>
                    </div>
                </section>
            </section>
        </ExpandedItems>
    </CollectionElementsProvider>
</template>

<script>
import { CollectionElementsProvider } from "components/providers/storeProviders";
import { updateContentFields } from "components/History/model/queries";
import ContentItem from "components/History/Content/ContentItem";
import CollectionNavigation from "./CollectionNavigation";
import CollectionOperations from "./CollectionOperations";
import CollectionDetails from "./CollectionDetails";
import ExpandedItems from "components/History/Content/ExpandedItems";
import Listing from "components/History/Layout/Listing";

export default {
    components: {
        CollectionDetails,
        CollectionElementsProvider,
        CollectionNavigation,
        CollectionOperations,
        ContentItem,
        ExpandedItems,
        Listing,
    },
    props: {
        history: { type: Object, required: true },
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
