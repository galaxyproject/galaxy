<template>
    <DscUI
        v-if="dsc"
        v-bind="$attrs"
        v-on="$listeners"
        class="dataset-collection"
        :dsc="dsc"
        @update:dsc="$emit('update:item', $event)"
        @delete="onDelete"
        @undelete="onUndelete"
        @unhide="onUnhide"
    />
</template>

<script>
import DscUI from "./DscUI";
import { DatasetCollection } from "../../model";
import { deleteDatasetCollection } from "../../model/queries";
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
    },
};
</script>
