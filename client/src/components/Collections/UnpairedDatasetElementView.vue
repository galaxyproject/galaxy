<template>
    <li class="dataset unpaired" @click="$emit('element-is-selected', element)">
        <label>
            {{ element.name }}
        </label>
    </li>
</template>

<script>
import _l from "utils/localization";
export default {
    props: {
        element: {
            required: true,
        },
    },
    data: function () {
        return {
            titleElementName: _l("Click to rename"),
            isSelected: false,
        };
    },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
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
