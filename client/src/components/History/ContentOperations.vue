<template>
    <section>
        <!-- header always visible, has current selection count and drill menu -->
        <header class="d-flex align-items-center justify-content-between">
            <!-- toggle between direct item selection and query-based selection -->
            <checkbox size="sm" :checked="useItemSelection" @change="toggleSelectionMode" />

            <!-- either direct item selection: count the set size, or query-based selection which will
            operate on a query selection on the server -->
            <h6 class="text-nowrap mr-3" v-if="useItemSelection">
                <span v-localize>Items Selected</span>
                <span>{{ contentSelection.size }}</span>
            </h6>
            <h6 class="text-nowrap mr-3" v-else>
                <span v-localize>Total Matches</span>
                <span>{{ queryMatches }}</span>
            </h6>

            <PriorityMenu :starting-height="27">
                <PriorityMenuItem
                    key="filter"
                    title="Filter History Content"
                    icon="fa fa-filter"
                    @click="showFilters = !showFilters"
                    :pressed="showFilters"
                />
                <PriorityMenuItem
                    key="collapse-expanded"
                    title="Collapse Expanded Datasets"
                    icon="fas fa-compress-alt"
                    @click="$emit('collapseAllContent')"
                />
            </PriorityMenu>
        </header>

        <!-- describe content filters, or toggle single-item selection mode -->
        <ContentFilters v-if="showFilters" class="content-filters mt-1" :filters="filters" v-on="$listeners" />

        <!-- pick an operation to use on the selection -->
        <b-input-group v-if="showFilters">
            <b-form-select v-model="operation" :options="operations" :disabled="!hasSelection" />
            <b-button v-b-modal.confirm-execution>
                <span v-localize>Execute</span>
            </b-button>
        </b-input-group>

        <!-- confirmation modal -->
        <b-modal id="confirm-execution" title="Execute operation?" @ok="$emit('executeOperation', operation)">
            <p>You are about to execute operation Blah on X rows.</p>
        </b-modal>
    </section>
</template>

<script>
import { SearchParams, History } from "./model";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import { BModal, BInputGroup, BButton, BFormCheckbox as Checkbox } from "bootstrap-vue";
import { PriorityMenu, PriorityMenuItem } from "components/PriorityMenu";
import ContentFilters from "./ContentFilters";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        BModal,
        BInputGroup,
        BButton,
        Checkbox,
        ContentFilters,
        PriorityMenu,
        PriorityMenuItem,
    },
    props: {
        history: { type: History, required: true },
        filters: { type: SearchParams, required: true },
        queryMatches: { type: Number, default: 0 },
        useItemSelection: { type: Boolean, required: true },
        contentSelection: { type: Set, required: true },
        operations: { type: Array, required: true },
    },
    data() {
        return {
            showFilters: false,
            operation: null,
        };
    },
    computed: {
        hasSelection() {
            return this.queryMatches > 0 || this.contentSelection.size > 0;
        },
    },
    methods: {
        toggleSelectionMode(useItems) {
            if (!useItems) {
                this.$emit("resetSelection");
            }
            this.$emit("update:useItemSelection", useItems);
        },
    },
};
</script>
