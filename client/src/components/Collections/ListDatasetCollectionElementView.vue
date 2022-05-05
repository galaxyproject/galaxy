<template>
    <div class="collection-element" @click="$emit('element-is-selected', element)">
        <click-to-edit v-model="elementName" :title="titleElementName" />
        <button class="discard-btn btn-sm" :title="titleDiscardButton" @click="clickDiscard">
            {{ l("Discard") }}
        </button>
    </div>
</template>

<script>
import _l from "utils/localization";
import ClickToEdit from "./common/ClickToEdit";
export default {
    components: { ClickToEdit },
    props: {
        element: {
            required: true,
        },
    },
    data: function () {
        return {
            titleDiscardButton: _l("Remove this dataset from the list"),
            titleElementName: _l("Click to rename"),
            isSelected: false,
            elementName: "",
        };
    },
    watch: {
        elementName() {
            this.$emit("onRename", this.elementName);
        },
    },
    created: function () {
        this.elementName = this.element.name;
    },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
        clickDiscard: function () {
            this.$emit("element-is-discarded", this.element);
        },
        /** string rep */
        toString() {
            return "ListDatasetCollectionElementView()";
        },
    },
};
</script>

<style>
.discard-btn {
    float: right;
}
.collection-element {
    height: auto;
}
</style>
