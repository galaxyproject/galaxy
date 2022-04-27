<template>
    <b-button-group size="sm">
        <b-button v-if="hasSelection" variant="link" data-test-id="clear-btn" @click="resetSelection">
            <span class="fa fa-fw fa-times" title="Clear selection" />
        </b-button>
        <b-button v-else variant="link" data-test-id="select-all-btn" @click="selectAll">
            <span>Select All</span>
        </b-button>
    </b-button-group>
</template>

<script>
import { BButton, BButtonGroup } from "bootstrap-vue";

export default {
    components: {
        "b-button": BButton,
        "b-button-group": BButtonGroup,
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
