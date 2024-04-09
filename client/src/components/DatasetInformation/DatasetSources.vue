<script setup lang="ts">
import { type DatasetTransform } from "@/api";

import DatasetSource from "@/components/DatasetInformation/DatasetSource.vue";

interface Props {
    sources: {
        source_uri: string;
        transform: DatasetTransform[];
    }[];
}

defineProps<Props>();
</script>

<template>
    <span class="dataset-sources">
        <ul class="dataset-sources-list">
            <DatasetSource v-for="(source, index) in sources" :key="index" :source="source" />
        </ul>
    </span>
</template>

<style scoped>
.dataset-sources-list {
    padding-inline-start: 20px;
    margin-bottom: 0px;
}
</style>
