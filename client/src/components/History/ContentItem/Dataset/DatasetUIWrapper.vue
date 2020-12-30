<template>
    <DatasetUI
        v-if="dataset"
        v-bind="$attrs"
        v-on="$listeners"
        v-on:update:expanded="expand"
        :expanded="expanded"
        :dataset="dataset"
        :showTags="true"
        @deleteDataset="onDelete(dataset, $event)"
        @undeleteDataset="onUndelete(dataset, $event)"
        @unhideDataset="onUnhide(dataset, $event)"
        @updateDataset="onUpdate(dataset, $event)"
    >
    </DatasetUI>
</template>
<script>
import DatasetUI from "./DatasetUI";
import { Dataset } from "../../model/Dataset";
import { deleteContent, updateContentFields } from "../../model/queries";
import { cacheContent } from "../../caching";

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
            const element = { ...this.item };
            if (this.element_identifier) {
                element.name = this.element_identifier;
            }
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
