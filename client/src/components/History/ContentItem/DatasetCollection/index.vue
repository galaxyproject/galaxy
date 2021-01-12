<template>
    <DscUI
        v-if="dsc"
        v-bind="$attrs"
        v-on="$listeners"
        class="dataset-collection"
        :dsc="dsc"
        @hideCollection="onHide(dsc)"
        @unhideCollection="onUnhide(dsc, $event)"
        @deleteCollection="onDelete(dsc, $event)"
        @undeleteCollection="onUndelete(dsc)"
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
        async onDelete(collection, flags = {}) {
            const { recursive = false, purge = false } = flags;
            const result = await deleteDatasetCollection(collection, recursive, purge);
            if (result.deleted) {
                const newFields = Object.assign(collection, {
                    isDeleted: result.deleted,
                });
                await cacheContent(newFields);
            }
        },

        async onUndelete(collection) {
            console.log("onUndelete", ...arguments);
            // await updateDatasetCollection(collection, {
            //     deleted: false
            // });
        },
        // This a valid thing to do?
        async onHide(collection) {
            console.log("onHide", ...arguments);
            // await updateDatasetCollection(collection, {
            //     visible: false
            // });
        },
        async onUnhide(collection) {
            console.log("onUnhide", ...arguments);
            // console.log("hideCollection, can we do this?", collection);
            // await updateDatasetCollection(collection, {
            //     visible: true
            // });
        },
    },
};
</script>
