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
// import SubDataset from "./SubDataset";
import Subcollection from "./Subcollection";

export default {
    template: `
        <component :is="contentItemComponent"
            class="content-item p-1"
            :class="{ loading }"
            :tabindex="index"
            v-on="$listeners"
            v-bind="bindProps"
            @mouseover.native.self.stop="setFocus(index)"
            @keydown.native.arrow-up.self.stop="setFocus(index - 1)"
            @keydown.native.arrow-down.self.stop="setFocus(index + 1)"
        />
    `,

    components: {
        Placeholder,
        Dataset,
        DatasetCollection,
        // SubDataset,
        Subcollection,
    },

    props: {
        item: { type: Object, required: true },
        index: { type: Number, required: true },
    },

    data: () => ({
        suppressFocus: false,
    }),

    methods: {
        setFocus(index) {
            if (this.suppressFocus) return;
            const ul = this.$el.closest(".scroller");
            const el = ul.querySelector(`[tabindex="${index}"]`);
            if (el) el.focus();
        },
    },

    computed: {
        loading() {
            return !this.item;
        },
        contentItemComponent() {
            // override me
            return "Placeholder";
        },
        bindProps() {
            return { ...this.$props, ...this.$attrs };
        },
    },

    created() {
        this.$root.$on("bv::dropdown::show", () => (this.suppressFocus = true));
        this.$root.$on("bv::dropdown::hide", () => (this.suppressFocus = false));
    },
};
