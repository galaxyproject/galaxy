<template>
    <div class="text-center">
        <div v-if="!hasSelection">No items selected</div>
        <div v-else>
            <div v-if="isQuerySelection">
                <div v-if="hasFilters">All {{ totalItemsInQuery }} items that match the filters are selected</div>
                <div v-else>All {{ totalItemsInQuery }} active items in history are selected</div>
            </div>
            <div v-else>{{ selectionSize }} items selected</div>
        </div>
        <div v-if="canSelectAll">
            <b-link @click="onSelectAllItemsInQuery">
                {{ selectAllOptionText }}
            </b-link>
        </div>
        <b-link v-if="hasSelection" @click="clearSelection"> Clear selection </b-link>
    </div>
</template>

<script>
export default {
    props: {
        hasFilters: { type: Boolean, required: true },
        isQuerySelection: { type: Boolean, required: true },
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
        selectAllOptionText() {
            return this.hasFilters
                ? `Select all ${this.totalItemsInQuery} items that match the current filters`
                : `Select all ${this.totalItemsInQuery} active items in history`;
        },
        /** @returns {Boolean} */
        selectionMatchesQuery() {
            if (this.isQuerySelection) {
                return true;
            }
            return this.hasFilters
                ? this.numTotalItemsInCurrentSearch === this.selectionSize
                : this.numTotalItemsInHistory === this.selectionSize;
        },
    },
    methods: {
        onSelectAllItemsInQuery() {
            this.$emit("select-all", this.numTotalItemsInHistory);
        },
        clearSelection() {
            this.$emit("clear-selection");
        },
    },
};
</script>
