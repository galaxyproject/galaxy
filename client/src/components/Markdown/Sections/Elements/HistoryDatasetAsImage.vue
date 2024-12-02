<script setup lang="ts">
import DatasetAsImage from "@/components/Dataset/DatasetAsImage/DatasetAsImage.vue";

interface DatasetAsImageArgs {
    history_dataset_id: string;
    path?: string;
}

interface Props {
    args: DatasetAsImageArgs;
}

const props = defineProps<Props>();
</script>

<template>
    <div>
        <DatasetAsImage :path="props.args.path" :history-dataset-id="props.args.history_dataset_id" />
    </div>
</template>
