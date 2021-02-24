<!-- For each element in the history, this selects whether it will be displayed as a dataset or a dataset collection -->

<template>
    <component
        :is="contentItemComponent"
        class="content-item p-1"
        v-on="$listeners"
        v-bind="$attrs"
        :index="index"
        :tabindex="index"
        :item="localItem"
        @update:item="onUpdate"
        @delete="onDelete"
        @undelete="onUndelete"
        @unhide="onUnhide"
        @mouseover.native.self.stop="setFocus(index)"
        @keydown.native.arrow-up.self.stop="setFocus(index - 1)"
        @keydown.native.arrow-down.self.stop="setFocus(index + 1)"
    />
</template>

<script>
import Placeholder from "./Placeholder";
import Dataset from "./Dataset";
import DatasetCollection from "./DatasetCollection";
import Focusable from "./Focusable";
import { Content } from "../model";
import { deleteContent, updateContentFields } from "../model/queries";
import { cacheContent } from "../caching";

/**
 * A component representing a direct child of the history. Datasets and collections not nested
 * inside a collection.
 */
export default {
    components: {
        Placeholder,
        Dataset,
        DatasetCollection,
    },

    mixins: [Focusable],

    props: {
        /**
         * Content result, raw props for either a dataset or dataset collection at the root of the history.
         *
         * @var {Object}
         */
        item: { type: Object, required: true, validator: Content.isValidContentProps },

        /**
         * Number in the currently rendered list of content. This is not an index representing the
         * position in the history, just the current list of rendered list.
         */
        index: { type: Number, required: true },
    },

    data() {
        return {
            // creating a localItem for the content data allows us
            // to do immediate updates as well as accept updates from
            // the cache content provider
            localItem: this.item,
        };
    },

    watch: {
        item(newItem) {
            this.localItem = newItem;
        },
    },

    computed: {
        contentItemComponent() {
            const { history_content_type } = this.item;
            switch (history_content_type) {
                case "dataset":
                    return "Dataset";
                case "dataset_collection":
                    return "DatasetCollection";
                default:
                    return "Placeholder";
            }
        },
    },

    methods: {
        async onDelete(opts = {}) {
            const ajaxResult = await deleteContent(this.localItem, opts);
            await cacheContent(ajaxResult);
        },
        async onUnhide() {
            await this.onUpdate({ visible: true });
        },
        async onUndelete() {
            await this.onUpdate({ deleted: false });
        },
        async onUpdate(changes) {
            const serverContent = await updateContentFields(this.localItem, changes);
            const cachedContent = await cacheContent(serverContent, true);
            this.localItem = cachedContent;
        },
    },
};
</script>
