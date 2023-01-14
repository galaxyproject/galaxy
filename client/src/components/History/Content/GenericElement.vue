<script setup>
import Vue from "vue";
import ContentItem from "./ContentItem";
import { ref } from "vue";

const props = defineProps({
    dsc: {
        type: Object,
        required: true,
    },
});

const expandCollections = ref({});
const expandDatasets = ref({});

function viewCollection(itemId) {
    Vue.set(this.expandCollections, itemId, !this.expandCollections[itemId]);
}

function viewDataset(itemId) {
    Vue.set(this.expandDatasets, itemId, !this.expandDatasets[itemId]);
}
</script>

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
            <div v-if="!!expandCollections[item.id]" class="mx-3">
                <GenericElement :dsc="item.object" />
            </div>
        </div>
    </div>
</template>
