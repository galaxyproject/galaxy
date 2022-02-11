<!-- a read-only dataset inside a collection. The collection query does not return enough
information to properly render the dataset, so what we do is look it up on expand, checking the
cache first to see if we already have the data -->

<template>
    <DatasetUI
        v-if="dataset"
        v-bind="$attrs"
        v-on="$listeners"
        :dataset="dataset"
        :writable="false"
        :selectable="false"
        @update:expanded="onExpand" />
</template>

<script>
import { Dataset } from "../model";
import { getContentDetails } from "../model/queries";
import DatasetUI from "./Dataset/DatasetUI";

export default {
    components: {
        DatasetUI,
    },
    props: {
        item: { type: Object, required: true },
    },
    data() {
        return {
            datasetObject: this.extractDataset(this.item),
            loading: false,
        };
    },
    computed: {
        dataset() {
            return new Dataset({ ...this.datasetObject });
        },
    },
    methods: {
        extractDataset() {
            return {
                id: this.item.object.id,
                element_identifier: this.item.element_identifier,
                state: this.item.object.state,
                history_id: this.item.object.history_id,
                history_content_type: "dataset",
                visible: true,
            };
        },
        onExpand(val) {
            if (val) {
                this.loadDetails();
            }
            this.$emit("update:expand", val);
        },
        async loadDetails() {
            this.datasetObject = await getContentDetails(this.datasetObject);
        },
    },
};
</script>
