<template>
    <div class="dataset" @click="$emit('element-is-selected', element)">
        <click-to-edit :element="element.name" :title="titleElementName" @renamed-element="renameElement" />
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
        /** string rep */
        toString() {
            return "PairedListDatasetCollectionElementView()";
        },
    },
};
</script>

<style>
.discard-btn {
    float: right;
}
</style>
