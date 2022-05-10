<template>
    <section v-if="hasSelection">
        <b-dropdown text="Selection" size="sm" variant="primary" data-description="selected content menu">
            <template v-slot:button-content>
                <span v-if="selectionMatchesQuery" data-test-id="all-filter-selected">
                    All <b>{{ totalItemsInQuery }}</b> selected
                </span>
                <span v-else data-test-id="num-active-selected">
                    <b>{{ selectionSize }}</b> of {{ totalItemsInQuery }} selected
                </span>
            </template>
            <b-dropdown-text>
                <span v-localize>With {{ numSelected }} selected...</span>
            </b-dropdown-text>
            <b-dropdown-item v-if="showHidden" v-b-modal:show-selected-content>
                <span v-localize>Unhide</span>
            </b-dropdown-item>
            <b-dropdown-item v-else v-b-modal:hide-selected-content>
                <span v-localize>Hide</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="showDeleted" v-b-modal:restore-selected-content>
                <span v-localize>Undelete</span>
            </b-dropdown-item>
            <b-dropdown-item v-else v-b-modal:delete-selected-content>
                <span v-localize>Delete</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="!showDeleted" v-b-modal:purge-selected-content>
                <span v-localize>Delete (permanently)</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="showBuildOptions" data-description="build list" @click="buildDatasetList">
                <span v-localize>Build Dataset List</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="showBuildOptions" data-description="build pair" @click="buildDatasetPair">
                <span v-localize>Build Dataset Pair</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="showBuildOptions" data-description="build list of pairs" @click="buildListOfPairs">
                <span v-localize>Build List of Dataset Pairs</span>
            </b-dropdown-item>
            <b-dropdown-item
                v-if="showBuildOptions"
                data-description="build collection from rules"
                @click="buildCollectionFromRules">
                <span v-localize>Build Collection from Rules</span>
            </b-dropdown-item>
        </b-dropdown>

        <b-modal id="hide-selected-content" title="Hide Selected Content?" title-tag="h2" @ok="hideSelected">
            <p v-localize>Really hide {{ numSelected }} content items?</p>
        </b-modal>
        <b-modal id="show-selected-content" title="Show Selected Content?" title-tag="h2" @ok="unhideSelected">
            <p v-localize>Really show {{ numSelected }} content items?</p>
        </b-modal>
        <b-modal id="delete-selected-content" title="Delete Selected Content?" title-tag="h2" @ok="deleteSelected">
            <p v-localize>Really delete {{ numSelected }} content items?</p>
        </b-modal>
        <b-modal id="restore-selected-content" title="Restore Selected Content?" title-tag="h2" @ok="undeleteSelected">
            <p v-localize>Really restore {{ numSelected }} content items?</p>
        </b-modal>
        <b-modal id="purge-selected-content" title="Purge Selected Content?" title-tag="h2" @ok="purgeSelected">
            <p v-localize>Permanently delete {{ numSelected }} content items?</p>
            <p><strong v-localize class="text-danger">Warning, this operation cannot be undone.</strong></p>
        </b-modal>
    </section>
     <!-- Fix this: Is out of total items, not active -->
    <section v-else>
        <b>{{ totalItemsInQuery }}</b> of {{ Object.keys(history).length }} found
    </section>
</template>

<script>
import {
    hideSelectedContent,
    unhideSelectedContent,
    deleteSelectedContent,
    undeleteSelectedContent,
    purgeSelectedContent,
} from "components/History/model/crud";
import { createDatasetCollection } from "components/History/model/queries";
import { buildCollectionModal } from "components/History/adapters/buildCollectionModal";
import { checkFilter, getQueryDict } from "store/historyStore/model/filtering";

export default {
    props: {
        history: { type: Object, required: true },
        filterText: { type: String, required: true },
        contentSelection: { type: Map, required: true },
        selectionSize: { type: Number, required: true },
        isQuerySelection: { type: Boolean, required: true },
        totalItemsInQuery: { type: Number, required: false, default: 0 },
    },
    computed: {
        /** @returns {Boolean} */
        showHidden() {
            return checkFilter(this.filterText, "visible", false);
        },
        /** @returns {Boolean} */
        showDeleted() {
            return checkFilter(this.filterText, "deleted", true);
        },
        /** @returns {Boolean} */
        showBuildOptions() {
            return !this.isQuerySelection && !this.showHidden && !this.showDeleted;
        },
        /** @returns {Number} */
        numSelected() {
            return this.selectionSize;
        },
        /** @returns {Boolean} */
        hasSelection() {
            return this.numSelected > 0;
        },
        /** @returns {Boolean} */
        selectionMatchesQuery() {
            return this.totalItemsInQuery === this.selectionSize;
        },
    },
    watch: {
        hasSelection(newVal) {
            if (newVal) {
                this.$emit("update:show-selection", true);
            }
        },
    },
    methods: {
        // Selected content manipulation, hide/show/delete/purge
        async hideSelected() {
            await this.runOnSelection(hideSelectedContent);
        },
        async unhideSelected() {
            await this.runOnSelection(unhideSelectedContent);
        },
        async deleteSelected() {
            await this.runOnSelection(deleteSelectedContent);
        },
        async undeleteSelected() {
            await this.runOnSelection(undeleteSelectedContent);
        },
        async purgeSelected() {
            await this.runOnSelection(purgeSelectedContent);
        },
        async runOnSelection(operation) {
            this.$emit("update:operation-running", true);
            const items = this.getExplicitlySelectedItems();
            const filters = getQueryDict(this.filterText);
            this.$emit("update:show-selection", false);
            await operation(this.history, filters, items);
            this.$emit("update:operation-running", false);
        },
        getExplicitlySelectedItems() {
            if (this.isQuerySelection) {
                return []; // No explicit items allowed in query selection
            }
            const items = Array.from(this.contentSelection.values()).map((item) => {
                return { id: item.id, history_content_type: item.history_content_type };
            });
            return items;
        },

        // collection creation, fires up a modal
        async buildDatasetList() {
            await this.buildNewCollection("list");
        },
        async buildDatasetPair() {
            await this.buildNewCollection("paired");
        },
        async buildListOfPairs() {
            await this.buildNewCollection("list:paired");
        },
        async buildCollectionFromRules() {
            await this.buildNewCollection("rules");
        },
        async buildNewCollection(collectionType) {
            const modalResult = await buildCollectionModal(collectionType, this.history.id, this.contentSelection);
            await createDatasetCollection(this.history, modalResult);

            // have to hide the source items if that was requested
            if (modalResult.hide_source_items) {
                this.$emit("hide-selection", this.contentSelection);
                this.$emit("reset-selection");
            }
        },
    },
};
</script>
