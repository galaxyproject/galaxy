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
    methods: {
        contentItemComponent() {
            if (this.item.id === undefined) {
                return "Placeholder";
            }
            return this.historyContentItem();
        },
        historyContentItem() {
            const { history_content_type } = this.item;
            switch (history_content_type) {
                case "dataset":
                    return "Dataset";
                case "dataset_collection":
                    return "DatasetCollection";
                default:
                    return "Placeholder";
            }
        },
        collectionContentItem() {
            const { element_type } = this.item;
            switch (element_type) {
                case "hda":
                    return "Subdataset";
                case "hdca":
                    return "Subcollection";
                default:
                    return "Placeholder";
            }
        },
    },
};
</script>
