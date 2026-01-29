<script setup lang="ts">
import DatasetAsImage from "@/components/Dataset/DatasetAsImage/DatasetAsImage.vue";

interface Props {
    datasetId: string;
    path?: string;
}

defineProps<Props>();
</script>

<template>
    <div>
        <DatasetAsImage :path="path" :history-dataset-id="datasetId" />
    </div>
</template>
