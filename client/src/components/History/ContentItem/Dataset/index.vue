<template>
    <DatasetUI
        v-if="dataset"
        v-bind="$attrs"
        v-on="$listeners"
        :dataset="dataset"
        @deleteDataset="onDelete(dataset, $event)"
        @undeleteDataset="onUndelete(dataset, $event)"
        @unhideDataset="onUnhide(dataset, $event)"
        @updateDataset="onUpdate(dataset, $event)"
    />
</template>

<script>
import DatasetUI from "./DatasetUI";
import { Dataset } from "../../model";
import { deleteContent, updateContentFields } from "../../model/queries";
import { cacheContent } from "../../caching";

export default {
    components: {
        DatasetUI,
    },
    props: {
        item: { type: Object, required: true },
    },
    computed: {
        dataset() {
            return new Dataset(this.item);
        },
    },
    methods: {
        async onDelete(dataset, opts = {}) {
            const ajaxResult = await deleteContent(dataset, opts);
            await cacheContent(ajaxResult);
        },
        async onUnhide(dataset) {
            await this.onUpdate(dataset, { visible: true });
        },
        async onUndelete(dataset) {
            await this.onUpdate(dataset, { deleted: false });
        },
        async onUpdate(dataset, changes) {
            const newContent = await updateContentFields(dataset, changes);
            await cacheContent(newContent);
        },
    },
};
</script>
