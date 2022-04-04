<template>
    <div class="text-center p-0">
        <div v-if="canSelectAll || hasSelection">
            <b-button-group size="sm" class="mb-2">
                <b-button v-if="canSelectAll" @click="selectAllItemsInQuery">Select All</b-button>
                <b-button v-if="hasSelection" @click="clearSelection">Clear selection</b-button>
            </b-button-group>
        </div>

        <b-alert show :variant="selectionAlertVariant" class="mb-0 p-2">
            <div v-if="!hasSelection">No items selected</div>
            <div v-else>
                <div v-if="selectionMatchesQuery">
                    <div v-if="hasFilters">
                        All <b>{{ totalItemsInQuery }}</b> items that match the filters are selected
                    </div>
                    <div v-else>
                        All <b>{{ totalItemsInQuery }}</b> active items in history are selected
                    </div>
                </div>
                <div v-else>
                    <div v-if="hasFilters">
                        <b>{{ selectionSize }}</b> of {{ totalItemsInQuery }} items that match the filters are selected
                    </div>
                    <div v-else>
                        <b>{{ selectionSize }}</b> of {{ totalItemsInQuery }} active items in history are selected
                    </div>
                </div>
            </div>
        </b-alert>
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
        /** @returns {String} */
        selectionAlertVariant() {
            return this.hasSelection ? "info" : "secondary";
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
