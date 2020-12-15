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
import Subcollection from "./Subcollection";

export default {
    inject: ["listState", "isSelected", "isExpanded", "setSelected", "setExpanded"],

    template: `
        <component :is="contentItemComponent"
            class="content-item p-1"
            :class="{ loading }"
            :index="index"
            :tabindex="index"
            :item="item"
            :selected.sync="selected"
            :expanded.sync="expanded"
            :scrolling="scrolling"
            @mouseover.native.self.stop="setFocus(index)"
            @keydown.native.arrow-up.self.stop="setFocus(index - 1)"
            @keydown.native.arrow-down.self.stop="setFocus(index + 1)"
        />
    `,

    components: {
        Placeholder,
        Dataset,
        DatasetCollection,
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
        selected: {
            get() {
                return this.isSelected(this.item);
            },
            set(val) {
                this.setSelected(this.item, val);
            },
        },
        expanded: {
            get() {
                return this.isExpanded(this.item);
            },
            set(val) {
                this.setExpanded(this.item, val);
            },
        },
        scrolling() {
            return this.listState.scrolling;
        },
    },

    created() {
        this.$root.$on("bv::dropdown::show", () => (this.suppressFocus = true));
        this.$root.$on("bv::dropdown::hide", () => (this.suppressFocus = false));
    },
};
