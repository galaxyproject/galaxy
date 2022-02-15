<template>
    <div class="p-2 details">
        Content Details
        <h4 data-description="dataset name">{{ item.name || "(Dataset Name)" }}</h4>
    </div>
</template>

<script>
import Placeholder from "./Placeholder";
import Dataset from "./Dataset/Dataset";
import DatasetCollection from "./DatasetCollection";
import Subdataset from "./Subdataset";
import Subcollection from "./Subcollection";

export default {
    components: {
        Placeholder,
        Dataset,
        DatasetCollection,
        Subdataset,
        Subcollection,
    },
    props: {
        item: { type: Object, required: true },
    },
};
</script>
