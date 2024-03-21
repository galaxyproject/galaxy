<script setup lang="ts">
import DatasetLink from "@/components/Dataset/DatasetLink/DatasetLink.vue";

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
    <DatasetLink
        class="dataset-link"
        :history-dataset-id="props.args.history_dataset_id"
        :path="props.args.path"
        :label="props.args.label" />
</template>
