<template>
    <div class="text-center">
        <div v-if="canSelectAll || hasSelection">
            <b-button-group size="sm" class="m-0 p-0 w-100">
                <b-button
                    v-if="!hasSelection"
                    variant="secondary"
                    class="w-100"
                    disabled
                    data-test-id="empty-selection">
                    <div>No items selected</div>
                </b-button>
                <slot v-else name="selection-operations" />
                <b-button v-if="hasSelection" @click="clearSelection" data-test-id="clear-btn">
                    <span class="fa fa-fw fa-times" />
                </b-button>
                <b-button v-else @click="selectAllItemsInQuery" data-test-id="select-all-btn">
                    <span class="fa fa-fw fa-check-double" />
                </b-button>
            </b-button-group>
        </div>
    </div>
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
