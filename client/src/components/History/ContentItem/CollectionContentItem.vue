<!-- For each element in the selected collection, this determines whether an individiual item will
be displayed as a subcollection or dataset element of a collection -->

<template>
    <component
        :is="contentItemComponent"
        class="content-item p-1"
        v-on="$listeners"
        v-bind="$attrs"
        :index="index"
        :tabindex="index"
        :item="item"
        :writable="false"
        @mouseover.native.self.stop="setFocus(index)"
        @keydown.native.arrow-up.self.stop="setFocus(index - 1)"
        @keydown.native.arrow-down.self.stop="setFocus(index + 1)"
    />
</template>

<script>
import Placeholder from "./Placeholder";
import Subdataset from "./Subdataset";
import Subcollection from "./Subcollection";
import Focusable from "./Focusable";
import { DatasetCollection } from "../model";

export default {
    components: {
        Placeholder,
        Subdataset,
        Subcollection,
    },

    mixins: [Focusable],

    props: {
        item: { type: Object, required: true, validator: DatasetCollection.isValidCollectionProps },
        index: { type: Number, required: true },
    },

    computed: {
        contentItemComponent() {
            const { history_content_type } = this.item;
            switch (history_content_type) {
                case "dataset":
                    return "Subdataset";
                case "dataset_collection":
                    return "Subcollection";
                default:
                    return "Placeholder";
            }
        },
    },
};
</script>
