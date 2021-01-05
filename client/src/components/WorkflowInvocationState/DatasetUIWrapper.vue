<!-- controls display of DisplayUI and delegates modifications -->
<template>
    <DatasetUI
        v-if="dataset"
        v-bind="$attrs"
        v-on="$listeners"
        @update:expanded="expand"
        :expanded="expanded"
        :dataset="dataset"
        :show-tags="true"
        @deleteDataset="onDelete(dataset, $event)"
        @undeleteDataset="onUndelete(dataset, $event)"
        @unhideDataset="onUnhide(dataset, $event)"
        @updateDataset="onUpdate(dataset, $event)"
    >
    </DatasetUI>
</template>
<script>
import DatasetUI from "../History/ContentItem/Dataset/DatasetUI";
import { Dataset } from "../History/model";
import { deleteContent, updateContentFields } from "../History/model/queries";
import { cacheContent } from "../History/caching";

export default {
    components: {
        DatasetUI,
    },
    props: {
        item: { type: Object, required: true },
        element_identifier: { type: String, required: false, default: "" },
    },
    computed: {
        dataset() {
            const element = { ...this.item, element_identifier: this.element_identifier };
            return new Dataset(element);
        },
    },
    data() {
        return {
            expanded: false,
        };
    },
    methods: {
        expand(event) {
            this.expanded = !this.expanded;
        },
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
