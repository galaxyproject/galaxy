<script setup lang="ts">
import { type PropType, ref, set } from "vue";

import { type components } from "@/api/schema";

import ContentItem from "./ContentItem.vue";

defineProps({
    dsc: {
        type: Object as PropType<components["schemas"]["DCObject"]>,
        required: true,
    },
});

const expandCollections = ref({});
const expandDatasets = ref({});

function toggle(expansionMap: Record<string, boolean>, itemId: string) {
    set(expansionMap, itemId, !expansionMap[itemId]);
}
</script>

<template>
    <div>
        <div v-for="(item, index) in dsc.elements" :key="index">
            <ContentItem
                :id="item.element_index + 1"
                :item="item.object"
                :name="item.element_identifier"
                :is-dataset="item.element_type == 'hda'"
                :expand-dataset="!!expandDatasets[item.id]"
                class="mx-3"
                @update:expand-dataset="toggle(expandDatasets, item.id)"
                @view-collection="toggle(expandCollections, item.id)" />
            <div v-if="!!expandCollections[item.id]" class="mx-3">
                <GenericElement :dsc="item.object" />
            </div>
        </div>
    </div>
</template>
