<template>
    <DatasetUI
        v-if="dataset"
        v-bind="$attrs"
        v-on="$listeners"
        :dataset="dataset"
        @update:dataset="onUpdate"
        @delete="onDelete"
        @undelete="onUndelete"
        @unhide="onUnhide"
        @copy-link="onCopyLink" />
</template>

<script>
import DatasetUI from "./DatasetUI";
import { Dataset } from "../../model";
import { deleteContent, updateContentFields } from "../../model/queries";
import { copy as sendToClipboard } from "utils/clipboard";
import { absPath } from "utils/redirect";

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
        async onDelete(opts = {}) {
            await deleteContent(this.item, opts);
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
        onCopyLink() {
            const relPath = this.dataset.getUrl("download");
            const msg = this.localize("Link is copied to your clipboard");
            sendToClipboard(absPath(relPath), msg);
        },
    },
};
</script>
