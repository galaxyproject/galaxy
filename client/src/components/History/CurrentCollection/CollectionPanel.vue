<!-- When a dataset collection is being viewed, this panel shows the contents of that collection -->

<template>
    <ExpandedItems v-slot="{ isExpanded, setExpanded }" :scope-key="dsc.id" :get-item-key="(item) => item.id">
        <section class="dataset-collection-panel w-100 d-flex flex-column">
            <section>
                <CollectionNavigation
                    :history-name="history.name"
                    :selected-collections="selectedCollections"
                    v-on="$listeners" />
                <CollectionDetails :dsc="dsc" :writeable="isRoot" @update:dsc="updateDsc(dsc, $event)" />
                <CollectionOperations v-if="isRoot && showControls" :dsc="dsc" />
            </section>
            <section class="position-relative flex-grow-1 scroller">
                <div>
                    <ListingLayout :items="collectionElements" :loading="loading" @scroll="onScroll">
                        <template v-slot:item="{ item }">
                            <ContentItem
                                :id="item.element_index + 1"
                                :item="item.object"
                                :name="item.element_identifier"
                                :expand-dataset="isExpanded(item)"
                                :is-dataset="item.element_type == 'hda'"
                                :filterable="filterable"
                                @update:expand-dataset="setExpanded(item, $event)"
                                @view-collection="onViewSubCollection" />
                        </template>
                    </ListingLayout>
                </div>
            </section>
        </section>
    </ExpandedItems>
</template>

<script>
import ContentItem from "components/History/Content/ContentItem";
import ExpandedItems from "components/History/Content/ExpandedItems";
import ListingLayout from "components/History/Layout/ListingLayout";
import { updateContentFields } from "components/History/model/queries";
import { computed, ref } from "vue";

import { useCollectionElementsStore } from "@/stores/collectionElementsStore";

import CollectionDetails from "./CollectionDetails";
import CollectionNavigation from "./CollectionNavigation";
import CollectionOperations from "./CollectionOperations";

export default {
    components: {
        CollectionDetails,
        CollectionNavigation,
        CollectionOperations,
        ContentItem,
        ExpandedItems,
        ListingLayout,
    },
    props: {
        history: { type: Object, required: true },
        selectedCollections: { type: Array, required: true },
        showControls: { type: Boolean, default: true },
        filterable: { type: Boolean, default: false },
    },
    setup(props) {
        const collectionElementsStore = useCollectionElementsStore();
        const offset = ref(0);
        const dsc = computed(() => props.selectedCollections[props.selectedCollections.length - 1]);
        const collectionElements = computed(() =>
            collectionElementsStore.getCollectionElements(dsc.value, offset.value)
        );
        const loading = computed(() => collectionElementsStore.isLoadingCollectionElements(dsc.value));
        return { dsc, offset, collectionElements, loading };
    },
    computed: {
        jobState() {
            return this.dsc["job_state_summary"];
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
    watch: {
        history(newHistory, oldHistory) {
            if (newHistory.id != oldHistory.id) {
                // Send up event closing out selected collection on history change.
                this.$emit("update:selected-collections", []);
            }
        },
        jobState: {
            handler() {
                this.$refs.provider.load();
            },
            deep: true,
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
