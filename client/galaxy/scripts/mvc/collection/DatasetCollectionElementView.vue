<template>
    <div
        class="collection-element"
        @click="selectElement()"
    >
        <a class="name" title="titleElementName" href="javascript:void(0)" role="button" @click="clickName">
            {{ element.name }}
        </a>
        <button class="discard-btn btn-sm" title="titleDiscardButton" @click="clickDiscard">
            {{ l("Discard") }}
        </button>
    </div>
</template>

<script>
import _l from "utils/localization";
export default {
    props: {
        //TODO: do we need a prop for attributes?
        element: {
            required: true,
        },
    },
    data: function () {
        return {
            tagName: "li",
            className: "collection-element",
            titleDiscardButton: _l("Remove this dataset from the list"),
            titleElementName: _l("Click to rename"),
        };
    },
    computed: {},
    methods: {
        clickName: function () {
            var response = prompt(_l("Enter a new name for the element"), this.element.name);

            if (response) {
                this.element.name = response;
            }
            return this.element.name;
        },
        selectElement: function () {
            this.$emit('element-is-selected', this.element);
        },
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
        clickDiscard: function () {
            this.$emit('element-is-discarded', this.element);
            this.$destroy();
        },

        // },
        //TODO: template, rendering, OR conditional 'rendering (i.e. belongs in template)
        // /** dragging for re-ordering */
        // _dragend(ev) {
        //     this.$el.removeClass("dragging");
        //     this.$el.parent().trigger("collection-element.dragend", [this]);
        // },
        // /** dragging pairs for re-ordering */
        // _dragstart(ev) {
        //     if (ev.originalEvent) {
        //         ev = ev.originalEvent;
        //     }
        //     ev.dataTransfer.effectAllowed = "move";
        //     ev.dataTransfer.setData("text/plain", JSON.stringify(this.element));

        //     this.$el.addClass("dragging");
        //     this.$el.parent().trigger("collection-element.dragstart", [this]);
        // },

        //TODO: actual method - must be rewritten, assess whether methods/created/computed/etc.
        // /** animate the removal of this element and pub */
        // discard() {
        //     var view = this;
        //     var parentWidth = this.$el.parent().width();
        //     this.$el.animate({ "margin-right": parentWidth }, "fast", () => {
        //         view.trigger("discard", {
        //             source: view,
        //         });
        //         view.destroy();
        //     });
        // },
        /** string rep */
        toString() {
            return "DatasetCollectionElementView()";
        },
    },
};
</script>

<style>
.element-in-list {
    border-width: 1px 0px 1px 0px;
}
.discard-btn {
    float: right;
}
</style>
