<template>
    <div class="collection-element" @click="$emit('element-is-selected', element)">
        <!-- <a class="name" :title="titleElementName" href="javascript:void(0)" role="button" @click="clickName">
            {{ element.name }}
        </a> -->
        <click-to-edit :element="element.name" :title="titleElementName" @renamed-element="renameElement"/>
        <button class="discard-btn btn-sm" :title="titleDiscardButton" @click="clickDiscard">
            {{ l("Discard") }}
        </button>
    </div>
</template>

<script>
import _l from "utils/localization";
import ClickToEdit from "./common/ClickToEdit";
export default {
    props: {
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
            isSelected: false,
        };
    },
    components: { ClickToEdit },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
        renameElement: function (response) {
            this.element.name = response;
            return this.element.name;
        },
        clickDiscard: function () {
            this.$emit("element-is-discarded", this.element);
        },
        /** string rep */
        toString() {
            return "DatasetCollectionElementView()";
        },
    },
};
</script>

<style>
.discard-btn {
    float: right;
}
</style>
