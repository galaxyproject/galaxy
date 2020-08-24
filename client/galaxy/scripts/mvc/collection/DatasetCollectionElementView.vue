<template>
    <div>
        <a class="name" title="titleElementName" href="javascript:void(0)" role="button">
            {{ element.name }}
        </a>
        <button class="discard btn btn-sm" title="titleDiscardButton">
            _l("Discard")
        </button>
    </div>
</template>

<script>
import _l from "utils/localization";
export default {
    props: {
        //TODO: do we need a prop for attributes?
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
        };
    },
    methods: {
        /** select when the li is clicked */
        _click(ev) {
            ev.stopPropagation();
            this.select(ev);
        },
        /** discard when the discard button is clicked */
        _clickDiscard(ev) {
            ev.stopPropagation();
            this.discard();
        },
        /** rename a pair when the name is clicked */
        _clickName(ev) {
            ev.stopPropagation();
            ev.preventDefault();

            var response = prompt(`${_l("Enter a new name for the element")}:`, this.element.name);

            if (response) {
                this.element.name = response;
                this.render();
            }
            //TODO: cancelling with ESC leads to closure of the creator...
        },
        /** remove the DOM and any listeners */
        destroy() {
            this.off();
            this.$el.remove();
        },
        /** animate the removal of this element and pub */
        discard() {
            var view = this;
            var parentWidth = this.$el.parent().width();
            this.$el.animate({ "margin-right": parentWidth }, "fast", () => {
                view.trigger("discard", {
                    source: view,
                });
                view.destroy();
            });
        },
        /** dragging for re-ordering */
        _dragend(ev) {
            this.$el.removeClass("dragging");
            this.$el.parent().trigger("collection-element.dragend", [this]);
        },
        /** dragging pairs for re-ordering */
        _dragstart(ev) {
            if (ev.originalEvent) {
                ev = ev.originalEvent;
            }
            ev.dataTransfer.effectAllowed = "move";
            ev.dataTransfer.setData("text/plain", JSON.stringify(this.element));

            this.$el.addClass("dragging");
            this.$el.parent().trigger("collection-element.dragstart", [this]);
        },
        /** select this element and pub */
        select(toggle) {
            this.$el.toggleClass("selected", toggle);
            this.trigger("select", { source: this, selected: this.$el.hasClass("selected") });
        },
        /** manually bubble up an event to the parent/container */
        _sendToParent(ev) {
            this.$el.parent().trigger(ev);
        },
        /** string rep */
        toString() {
            return "DatasetCollectionElementView()";
        },
    },
    //initialize method
    created: {
        initialize: function (attributes) {
            this.element = attributes.element || {};
            this.selected = attributes.selected || false;
        },
    },
};
</script>
