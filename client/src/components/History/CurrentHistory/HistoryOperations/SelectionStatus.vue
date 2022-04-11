<template>
    <b-button-group v-if="canSelectAll || hasSelection" size="sm" class="text-primary">
        <b-button v-if="hasSelection" variant="link" @click="clearSelection" data-test-id="clear-btn">
            <span class="fa fa-fw fa-times" />
        </b-button>
        <b-button v-else variant="link" @click="selectAllItemsInQuery" data-test-id="select-all-btn">
            <span class="fa fa-fw fa-check-double" />
        </b-button>
    </b-button-group>
</template>

<script>
export default {
    props: {
        hasFilters: { type: Boolean, required: true },
        selectionSize: { type: Number, required: true },
        totalItemsInQuery: { type: Number, required: true },
    },
    computed: {
        /** @returns {Boolean} */
        hasSelection() {
            return this.selectionSize > 0;
        },
        /** @returns {Boolean} */
        canSelectAll() {
            return !this.selectionMatchesQuery;
        },
        /** @returns {Boolean} */
        selectionMatchesQuery() {
            return this.totalItemsInQuery === this.selectionSize;
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
