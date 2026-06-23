<script setup lang="ts">
import DatasetIndex from "@/components/Dataset/DatasetIndex/DatasetIndex.vue";

interface DatasetLinkArgs {
    history_dataset_id: string;
    path?: string;
    label?: string;
}

interface Props {
    args: DatasetLinkArgs;
}

const props = defineProps<Props>();
</script>

<template>
    <DatasetIndex class="dataset-index" :history-dataset-id="props.args.history_dataset_id" :path="props.args.path" />
</template>
