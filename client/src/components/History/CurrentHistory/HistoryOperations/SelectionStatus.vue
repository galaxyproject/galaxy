<template>
    <GButtonGroup size="sm">
        <GButton v-if="hasSelection" variant="link" data-test-id="clear-btn" @click="resetSelection">
            <span class="fa fa-fw fa-times" title="Clear selection" />
        </GButton>
        <GButton v-else variant="link" data-test-id="select-all-btn" @click="selectAll">
            <span>Select All</span>
        </GButton>
    </GButtonGroup>
</template>

<script>
import GButton from "component-library/GButton";
import GButtonGroup from "component-library/GButtonGroup";

export default {
    components: {
        GButton,
        GButtonGroup,
    },
    props: {
        selectionSize: { type: Number, required: true },
    },
    computed: {
        /** @returns {Boolean} */
        hasSelection() {
            return this.selectionSize > 0;
        },
    },
    methods: {
        selectAll() {
            this.$emit("select-all");
        },
        resetSelection() {
            this.$emit("reset-selection");
        },
    },
};
</script>
