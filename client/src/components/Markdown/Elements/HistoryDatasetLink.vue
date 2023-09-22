<template>
    <DatasetLink
        class="dataset-link"
        :history_dataset_id="args.history_dataset_id"
        :path="args.path"
        :label="args.label" />
</template>

<script>
import DatasetLink from "components/Dataset/DatasetLink/DatasetLink";
export default {
    components: {
        DatasetLink,
    },
    props: {
        args: {
            type: Object,
            default: null,
        },
    },
};
</script>
