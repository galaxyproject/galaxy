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
                <b-dropdown
                    v-else
                    text="Selection"
                    size="sm"
                    class="w-100"
                    toggle-class="text-decoration-none w-100"
                    data-description="selected content menu"
                    :variant="selectionAlertVariant">
                    <template v-slot:button-content>
                        <span v-if="selectionMatchesQuery" data-test-id="all-filter-selected">
                            All <b>{{ totalItemsInQuery }}</b> selected
                        </span>
                        <span v-else data-test-id="num-active-selected">
                            <b>{{ selectionSize }}</b> of {{ totalItemsInQuery }} selected
                        </span>
                    </template>
                    <b-dropdown-text>
                        <span v-localize>With {{ selectionSize }} selected...</span>
                    </b-dropdown-text>
                </b-dropdown>
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
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

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
