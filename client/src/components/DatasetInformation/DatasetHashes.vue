<script setup lang="ts">
import { type DatasetHash as DatasetHashType } from "@/api";

import DatasetHash from "@/components/DatasetInformation/DatasetHash.vue";

interface Props {
    hashes: DatasetHashType[];
}

defineProps<Props>();
</script>

<template>
    <span class="dataset-hashes">
        <ul class="dataset-hashes-list">
            <DatasetHash v-for="(hash, index) in hashes" :key="index" :hash="hash" />
        </ul>
    </span>
</template>

<style scoped lang="scss">
.dataset-hashes-list {
    padding-inline-start: 20px;
    margin-bottom: 0px;
}
</style>
