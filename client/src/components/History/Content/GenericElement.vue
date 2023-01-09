<template>
    <div>
        <div v-for="(item, index) in dsc.elements" :key="index">
            <ContentItem
                :id="item.element_index"
                :item="item.object"
                :name="item.element_identifier"
                :is-dataset="item.element_type == 'hda'"
                :expand-dataset="!!expandDatasets[item.id]"
                @update:expand-dataset="viewDataset(item.id)"
                @view-collection="viewCollection(item.id)" />
            <div v-if="!!expandCollections[item.id]">
                <GenericElementNode :dsc="item.object" />
            </div>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import ContentItem from "./ContentItem";
import { CollectionElementsProvider } from "components/providers/storeProviders";

export default {
    name: "GenericElementNode",
    components: {
        CollectionElementsProvider,
        ContentItem,
    },
    props: {
        dsc: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            expandCollections: {},
            expandDatasets: {},
        };
    },
    methods: {
        viewCollection(itemId) {
            Vue.set(this.expandCollections, itemId, !this.expandCollections[itemId]);
        },
        viewDataset(itemId) {
            Vue.set(this.expandDatasets, itemId, !this.expandDatasets[itemId]);
        },
    },
};
</script>
