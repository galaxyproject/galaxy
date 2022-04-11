<template>
    <b-button-group size="sm">
        <b-button v-if="hasSelection" variant="link" @click="resetSelection" data-test-id="clear-btn">
            <span class="fa fa-fw fa-times" />
        </b-button>
        <b-button v-else variant="link" class="text-decoration-none" @click="selectAll" data-test-id="select-all-btn">
            <span>Select All</span>
        </b-button>
    </b-button-group>
</template>

<script>
export default {
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
