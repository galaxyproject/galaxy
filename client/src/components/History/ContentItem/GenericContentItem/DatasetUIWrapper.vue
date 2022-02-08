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
        @delete="onDelete"
        @undelete="onUndelete"
        @unhide="onUnhide"
        @update="onUpdate">
    </DatasetUI>
</template>
<script>
import DatasetUI from "components/History/ContentItem/Dataset/DatasetUI";
import { Dataset } from "../../model";
import { deleteContent, updateContentFields } from "../../model/queries";

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
        async onDelete(opts = {}) {
            await deleteContent(this.dataset, opts);
        },
        async onUnhide() {
            await this.onUpdate({ visible: true });
        },
        async onUndelete() {
            await this.onUpdate({ deleted: false });
        },
        async onUpdate(changes = {}) {
            await updateContentFields(this.dataset, changes);
        },
    },
};
</script>
