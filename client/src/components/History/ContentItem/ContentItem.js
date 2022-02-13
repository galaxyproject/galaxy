/**
 * This is a single item in the list. The main job of the contentItem is to
 * pick a specific selector for the :is attribute of the generic component
 * placeholder. This should be a dataset, collection, or other component
 * depending on the specific list implementation.
 *
 * The mixin also pulls out "selected", and "expanded" properties which are
 * derived from the current component state rather than the data itself.
 */

import Placeholder from "./Placeholder";
import Dataset from "./Dataset";
import DatasetCollection from "./DatasetCollection";
import Subdataset from "./Subdataset";
import Subcollection from "./Subcollection";

export default {
    template: `
        <component :is="contentItemComponent"
            :data-ci-type="contentItemComponent"
            class="content-item"
            :class="{ loading }"
            :tabindex="index"
            :writable="writable"
            v-on="$listeners"
            v-bind="$attrs"
            :item="item"
            :index="index"
            :row-key="rowKey"
            :writable="writable"
            @mouseover.native.stop="setFocus(index)"
            @keydown.native.arrow-up.self.stop="setFocus(index - 1)"
            @keydown.native.arrow-down.self.stop="setFocus(index + 1)"
        />
    `,

    components: {
        Placeholder,
        Dataset,
        DatasetCollection,
        Subdataset,
        Subcollection,
    },

    props: {
        item: { type: Object, required: true },
        index: { type: Number, required: false, default: null },
        rowKey: { type: [Number, String], required: false, default: "" },
        writable: { type: Boolean, required: false, default: true },
    },

    data: () => ({
        suppressFocus: true,
    }),

    methods: {
        setFocus(index) {
            if (this.suppressFocus) {
                return;
            }
            const ul = this.$el.closest(".scroller");
            const el = ul.querySelector(`[tabindex="${index}"]`);
            if (el) {
                el.focus();
            }
        },
    },

    computed: {
        loading() {
            return !this.item;
        },
        contentItemComponent() {
            if (this.item.id === undefined) {
                return "Placeholder";
            }
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

    created() {
        this.$root.$on("bv::dropdown::show", () => (this.suppressFocus = true));
        this.$root.$on("bv::dropdown::hide", () => (this.suppressFocus = false));
    },
};
