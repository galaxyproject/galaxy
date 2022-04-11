<template>
    <b-button-group size="sm">
        <b-button v-if="hasSelection" variant="link" @click="clearSelection" data-test-id="clear-btn">
            <span class="fa fa-fw fa-times" />
        </b-button>
        <b-button
            v-else
            variant="link"
            class="text-decoration-none"
            @click="selectAllItemsInQuery"
            data-test-id="select-all-btn">
            <span class="fa fa-fw fa-check-double" />
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
        selectAllItemsInQuery() {
            this.$emit("select-all");
        },
        clearSelection() {
            this.$emit("clear-selection");
        },
    },
};
</script>
