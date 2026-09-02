<script setup lang="ts">
import DatasetCollectionElementPicker from "./DatasetCollectionElementPicker.vue";

defineProps<{
    datasetId?: string;
    collectionId?: string;
}>();
</script>

<template>
    <DatasetCollectionElementPicker v-if="collectionId" :hdca-id="collectionId">
        <template v-slot:element="{ element }">
            <slot v-if="element" :dataset-id="element"></slot>
        </template>
    </DatasetCollectionElementPicker>
    <div v-else-if="datasetId">
        <slot :dataset-id="datasetId" />
    </div>
</template>
