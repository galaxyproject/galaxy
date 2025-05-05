<script setup lang="ts">
import { type DatasetSource as DatasetSourceModel } from "@/api";

import DatasetSource from "@/components/DatasetInformation/DatasetSource.vue";

interface Props {
    sources: DatasetSourceModel[];
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
