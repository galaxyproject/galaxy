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
import { cacheContent } from "../../caching";

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
            const result = await deleteDatasetCollection(collection, recursive, purge);
            if (result.deleted) {
                const newFields = Object.assign(collection, {
                    isDeleted: result.deleted,
                });
                await cacheContent(newFields);
            }
        },
        async onUnhide() {
            await this.onUpdate({ visible: true });
        },
        async onUndelete() {
            await this.onUpdate({ deleted: false });
        },
        async onUpdate(changes) {
            const newContent = await updateContentFields(this.item, changes);
            await cacheContent(newContent);
        },
    },
};
</script>
