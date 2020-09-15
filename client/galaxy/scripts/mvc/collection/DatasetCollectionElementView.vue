<template>
    <div
        class="collection-element"
        v-bind:class="{ selected: isSelected }"
        @click="selectElement()"
    >
        <a class="name" title="titleElementName" href="javascript:void(0)" role="button" @click="clickName">
            {{ element.name }}
        </a>
        <button class="discard-btn btn-sm" title="titleDiscardButton">
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
        canHighlight: {
            type: Boolean,
            default: false
        }
    },
    data: function () {
        return {
            //TODO: how to make this private?
            //logNamespace: "collections",
            //TODO: use proper class (DatasetDCE or NestedDCDCE (or the union of both))
            tagName: "li",
            className: "collection-element",
            titleDiscardButton: _l("Remove this dataset from the list"),
            titleElementName: _l("Click to rename"),
            isSelected: false,
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
            this.isSelected = this.canHighlight && !this.isSelected;
            this.$emit('element-is-selected', this.element);
            console.log("selected " + this.element.name + " & emitted " + this.isSelected);
        },
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
        //move to computed after this is written.
        // discard: function () {

        // },
        //TODO: template, rendering, OR conditional rendering (i.e. belongs in template)
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
        // /** remove the DOM and any listeners */
        // destroy() {
        //     this.off();
        //     this.$el.remove();
        // },
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
        // /** manually bubble up an event to the parent/container */
        // _sendToParent(ev) {
        //     this.$el.parent().trigger(ev);
        // },
        // /** string rep */
        // toString() {
        //     return "DatasetCollectionElementView()";
        // },
    },
    //initialize method
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
