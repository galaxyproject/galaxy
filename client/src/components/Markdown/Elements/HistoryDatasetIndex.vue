<template>
    <DatasetIndex class="dataset-index" :history-dataset-id="args.history_dataset_id" :path="args.path" />
</template>

<script>
import DatasetIndex from "components/Dataset/DatasetIndex/DatasetIndex";

export default {
    components: {
        DatasetIndex,
    },
    props: {
        args: {
            type: Object,
            default: null,
        },
    },
};
</script>
