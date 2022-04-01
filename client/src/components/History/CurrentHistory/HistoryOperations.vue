<template>
    <section>
        <nav class="content-operations d-flex justify-content-between bg-secondary">
            <b-button-group>
                <b-button
                    title="Select Items"
                    class="show-history-content-selectors-btn rounded-0"
                    size="sm"
                    variant="link"
                    :disabled="!hasMatches"
                    :pressed="showSelection"
                    @click="toggleSelection">
                    <Icon icon="check-square" />
                </b-button>
                <b-button
                    title="Collapse Items"
                    class="rounded-0"
                    size="sm"
                    variant="link"
                    :disabled="!expandedCount"
                    @click="$emit('collapse-all')">
                    <Icon icon="compress" />
                </b-button>
            </b-button-group>
            <b-button-group>
                <b-dropdown
                    text="Selection"
                    size="sm"
                    variant="link"
                    toggle-class="text-decoration-none"
                    data-description="selected content menu"
                    :disabled="!hasSelection">
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
                    <b-dropdown-item v-if="showBuildOptions" @click="buildDatasetList" data-description="build list">
                        <span v-localize>Build Dataset List</span>
                    </b-dropdown-item>
                    <b-dropdown-item v-if="showBuildOptions" @click="buildDatasetPair" data-description="build pair">
                        <span v-localize>Build Dataset Pair</span>
                    </b-dropdown-item>
                    <b-dropdown-item
                        v-if="showBuildOptions"
                        @click="buildListOfPairs"
                        data-description="build list of pairs">
                        <span v-localize>Build List of Dataset Pairs</span>
                    </b-dropdown-item>
                    <b-dropdown-item
                        v-if="showBuildOptions"
                        @click="buildCollectionFromRules"
                        data-description="build collection from rules">
                        <span v-localize>Build Collection from Rules</span>
                    </b-dropdown-item>
                </b-dropdown>
                <b-dropdown
                    text="History"
                    size="sm"
                    variant="link"
                    class="rounded-0"
                    toggle-class="text-decoration-none"
                    data-description="history action menu"
                    :disabled="!hasMatches">
                    <b-dropdown-text id="history-op-all-content">
                        <span v-localize>With entire history...</span>
                    </b-dropdown-text>
                    <b-dropdown-item @click="onCopy" data-description="copy datasets">
                        <span v-localize>Copy Datasets</span>
                    </b-dropdown-item>
                    <b-dropdown-item v-b-modal:show-all-hidden-content>
                        <span v-localize>Unhide All Hidden Content</span>
                    </b-dropdown-item>
                    <b-dropdown-item v-b-modal:delete-all-hidden-content>
                        <span v-localize>Delete All Hidden Content</span>
                    </b-dropdown-item>
                    <b-dropdown-item v-b-modal:purge-all-deleted-content>
                        <span v-localize>Permanently Delete All Deleted Content</span>
                    </b-dropdown-item>
                </b-dropdown>
            </b-button-group>
        </nav>

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
            <p v-localize>Permanently delete {{ numSelected }} content items? This cannot be undone.</p>
        </b-modal>

        <b-modal id="show-all-hidden-content" title="Show Hidden Datasets" title-tag="h2" @ok="unhideAll">
            <p v-localize>Really unhide all hidden datasets?</p>
        </b-modal>

        <b-modal id="delete-all-hidden-content" title="Delete Hidden Datasets" title-tag="h2" @ok="deleteAllHidden">
            <p v-localize>Really delete all hidden datasets?</p>
        </b-modal>

        <b-modal id="purge-all-deleted-content" title="Purge Deleted Datasets" title-tag="h2" @ok="purgeAllDeleted">
            <p v-localize>"Really delete all deleted datasets permanently? This cannot be undone.</p>
        </b-modal>
    </section>
</template>

<script>
import { History } from "components/History/model/History";
import {
    hideSelectedContent,
    unhideSelectedContent,
    deleteSelectedContent,
    undeleteSelectedContent,
    purgeSelectedContent,
    unhideAllHiddenContent,
    deleteAllHiddenContent,
    purgeAllDeletedContent,
} from "components/History/model";
import { createDatasetCollection } from "components/History/model/queries";
import { buildCollectionModal } from "components/History/adapters/buildCollectionModal";
import { checkFilter, getQueryDict } from "store/historyStore/historyItemsFiltering";
import { iframeRedirect } from "components/plugins/legacyNavigation";
export default {
    props: {
        history: { type: History, required: true },
        filterText: { type: String, required: true },
        contentSelection: { type: Map, required: true },
        selectionSize: { type: Number, required: true },
        isQuerySelection: { type: Boolean, required: true },
        showSelection: { type: Boolean, required: true },
        hasMatches: { type: Boolean, required: true },
        expandedCount: { type: Number, required: false, default: 0 },
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
    },
    methods: {
        onCopy() {
            iframeRedirect("/dataset/copy_datasets");
        },
        toggleSelection() {
            this.$emit("update:show-selection", !this.showSelection);
        },

        // History-wide bulk updates, does server query first to determine "selection"
        async unhideAll(evt) {
            await unhideAllHiddenContent(this.history);
        },
        async deleteAllHidden(evt) {
            await deleteAllHiddenContent(this.history);
        },
        async purgeAllDeleted(evt) {
            await purgeAllDeletedContent(this.history);
        },

        // Selected content manipulation, hide/show/delete/purge
        hideSelected() {
            this.runOnSelection(hideSelectedContent);
        },
        unhideSelected() {
            this.runOnSelection(unhideSelectedContent);
        },
        deleteSelected() {
            this.runOnSelection(deleteSelectedContent);
        },
        undeleteSelected() {
            this.runOnSelection(undeleteSelectedContent);
        },
        purgeSelected() {
            this.runOnSelection(purgeSelectedContent);
        },
        async runOnSelection(fn) {
            const items = this.getExplicitlySelectedItems();
            const filters = getQueryDict(this.filterText);
            await fn(this.history, filters, items);
            this.$emit("reset-selection");
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
        async buildNewCollection(collectionTypeCode) {
            const modalResult = await buildCollectionModal(collectionTypeCode, this.history.id, this.contentSelection);
            await createDatasetCollection(this.history, modalResult);

            // have to hide the source items if that was requested
            if (modalResult.hide_source_items) {
                this.$emit("hide-selection", this.contentSelection);
                this.$emit("reset-selection");
            }
        },
    },
    watch: {
        hasSelection(newVal) {
            if (newVal) {
                this.$emit("update:show-selection", true);
            }
        },
    },
};
</script>

<style lang="scss">
// remove borders around buttons in menu
.content-operations .btn-group .btn {
    border-color: transparent !important;
}
</style>
