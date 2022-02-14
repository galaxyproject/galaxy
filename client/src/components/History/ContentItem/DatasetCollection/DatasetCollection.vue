<template>
    <DscUI
        v-if="dsc"
        v-bind="$attrs"
        v-on="$listeners"
        class="dataset-collection history-content"
        :dsc="dsc"
        @update:dsc="onUpdate"
        @delete="onDelete"
        @undelete="onUndelete"
        @unhide="onUnhide" />
</template>

<script>
import DscUI from "./DscUI";
import { DatasetCollection } from "../../model";
import { deleteDatasetCollection, updateContentFields } from "../../model/queries";

export default {
    components: {
        DscUI,
    },
    props: {
        item: { type: Object, required: true },
    },
    computed: {
        dsc() {
            return new DatasetCollection(this.item);
        },
    },
    methods: {
        async onDelete(flags = {}) {
            const { recursive = false, purge = false } = flags;
            const collection = this.item;
            await deleteDatasetCollection(collection, recursive, purge);
        },
        async onUnhide() {
            await this.onUpdate({ visible: true });
        },
        async onUndelete() {
            await this.onUpdate({ deleted: false });
        },
        async onUpdate(changes) {
            await updateContentFields(this.item, changes);
        },
    },
};
</script>
