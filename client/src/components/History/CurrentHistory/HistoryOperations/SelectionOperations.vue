<template>
    <section v-if="hasSelection">
        <ConfigProvider v-slot="{ config }">
            <b-dropdown text="Selection" size="sm" variant="primary" data-description="selected content menu" no-flip>
                <template v-slot:button-content>
                    <span v-if="selectionMatchesQuery" data-test-id="all-filter-selected">
                        All <b>{{ totalItemsInQuery }}</b> selected
                    </span>
                    <span v-else data-test-id="num-active-selected">
                        <b>{{ selectionSize }}</b> of {{ totalItemsInQuery }} selected
                    </span>
                </template>
                <b-dropdown-text>
                    <span v-localize data-description="selected count">With {{ numSelected }} selected...</span>
                </b-dropdown-text>
                <b-dropdown-item v-if="showHidden" v-b-modal:show-selected-content data-description="unhide option">
                    <span v-localize>Unhide</span>
                </b-dropdown-item>
                <b-dropdown-item v-else v-b-modal:hide-selected-content data-description="hide option">
                    <span v-localize>Hide</span>
                </b-dropdown-item>
                <b-dropdown-item
                    v-if="canUndeleteSelection"
                    v-b-modal:restore-selected-content
                    data-description="undelete option">
                    <span v-localize>Undelete</span>
                </b-dropdown-item>
                <b-dropdown-item v-if="!showDeleted" v-b-modal:delete-selected-content data-description="delete option">
                    <span v-localize>Delete</span>
                </b-dropdown-item>
                <b-dropdown-item v-b-modal:purge-selected-content data-description="purge option">
                    <span v-localize>Delete (permanently)</span>
                </b-dropdown-item>
                <b-dropdown-divider v-if="showBuildOptions" />
                <b-dropdown-item v-if="showBuildOptions" data-description="build list" @click="buildDatasetList">
                    <span v-localize>Build Dataset List</span>
                </b-dropdown-item>
                <b-dropdown-item v-if="showBuildOptions" data-description="build pair" @click="buildDatasetPair">
                    <span v-localize>Build Dataset Pair</span>
                </b-dropdown-item>
                <b-dropdown-item
                    v-if="showBuildOptions"
                    data-description="build list of pairs"
                    @click="buildListOfPairs">
                    <span v-localize>Build List of Dataset Pairs</span>
                </b-dropdown-item>
                <b-dropdown-item
                    v-if="showBuildOptions"
                    data-description="build collection from rules"
                    @click="buildCollectionFromRules">
                    <span v-localize>Build Collection from Rules</span>
                </b-dropdown-item>
                <b-dropdown-divider />
                <b-dropdown-item v-b-modal:change-dbkey-of-selected-content data-description="change database build">
                    <span v-localize>Change Database/Build</span>
                </b-dropdown-item>
                <b-dropdown-item
                    v-if="config.enable_celery_tasks"
                    v-b-modal:change-datatype-of-selected-content
                    data-description="change data type">
                    <span v-localize>Change data type</span>
                </b-dropdown-item>
                <b-dropdown-item v-b-modal:add-tags-to-selected-content data-description="add tags">
                    <span v-localize>Add tags</span>
                </b-dropdown-item>
                <b-dropdown-item v-b-modal:remove-tags-from-selected-content data-description="remove tags">
                    <span v-localize>Remove tags</span>
                </b-dropdown-item>
            </b-dropdown>
        </ConfigProvider>

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
        <b-modal
            id="change-dbkey-of-selected-content"
            title="Change Database/Build?"
            title-tag="h2"
            @ok="changeDbkeyOfSelected">
            <p v-localize>Select a new Database/Build for {{ numSelected }} items:</p>
            <GenomeProvider v-slot="{ item: dbkeys, loading: loadingDbKeys }">
                <SingleItemSelector
                    collection-name="Database/Builds"
                    :loading="loadingDbKeys"
                    :items="dbkeys"
                    :current-item-id="selectedDbKey"
                    class="mb-5 pb-5"
                    @update:selected-item="onSelectedDbKey" />
            </GenomeProvider>
        </b-modal>
        <b-modal
            id="change-datatype-of-selected-content"
            title="Change data type?"
            title-tag="h2"
            :ok-disabled="selectedDatatype == null"
            @ok="changeDatatypeOfSelected">
            <p v-localize>Select a new data type for {{ numSelected }} items:</p>
            <DatatypesProvider v-slot="{ item: datatypes, loading: loadingDatatypes }">
                <SingleItemSelector
                    collection-name="Data Types"
                    :loading="loadingDatatypes"
                    :items="datatypes"
                    :current-item-id="selectedDatatype"
                    class="mb-5 pb-5"
                    @update:selected-item="onSelectedDatatype" />
            </DatatypesProvider>
        </b-modal>
        <b-modal
            id="add-tags-to-selected-content"
            title="Add tags?"
            title-tag="h2"
            :ok-disabled="noTagsSelected"
            @ok="addTagsToSelected">
            <p v-localize>Apply the following tags to {{ numSelected }} items:</p>
            <StatelessTags v-model="selectedTags" class="tags" />
        </b-modal>
        <b-modal
            id="remove-tags-from-selected-content"
            title="Remove tags?"
            title-tag="h2"
            :ok-disabled="noTagsSelected"
            @ok="removeTagsFromSelected">
            <p v-localize>Remove the following tags from {{ numSelected }} items:</p>
            <StatelessTags v-model="selectedTags" class="tags" />
        </b-modal>
    </section>
</template>

<script>
import {
    hideSelectedContent,
    unhideSelectedContent,
    deleteSelectedContent,
    undeleteSelectedContent,
    purgeSelectedContent,
    changeDbkeyOfSelectedContent,
    changeDatatypeOfSelectedContent,
    addTagsToSelectedContent,
    removeTagsFromSelectedContent,
} from "components/History/model/crud";
import { createDatasetCollection } from "components/History/model/queries";
import { buildCollectionModal } from "components/History/adapters/buildCollectionModal";
import { checkFilter, getQueryDict } from "store/historyStore/model/filtering";
import { GenomeProvider, DatatypesProvider } from "components/providers";
import SingleItemSelector from "components/SingleItemSelector";
import { StatelessTags } from "components/Tags";
import ConfigProvider from "components/providers/ConfigProvider";

export default {
    components: {
        GenomeProvider,
        DatatypesProvider,
        SingleItemSelector,
        StatelessTags,
        ConfigProvider,
    },
    props: {
        history: { type: Object, required: true },
        filterText: { type: String, required: true },
        contentSelection: { type: Map, required: true },
        selectionSize: { type: Number, required: true },
        isQuerySelection: { type: Boolean, required: true },
        totalItemsInQuery: { type: Number, default: 0 },
    },
    data: function () {
        return {
            selectedDbKey: "?",
            selectedDatatype: "auto",
            selectedTags: [],
        };
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
        noTagsSelected() {
            return this.selectedTags.length === 0;
        },
        canUndeleteSelection() {
            return this.showDeleted && (this.isQuerySelection || !this.areAllSelectedPurged);
        },
        areAllSelectedPurged() {
            for (const item of this.contentSelection.values()) {
                if (Object.prototype.hasOwnProperty.call(item, "purged") && !item["purged"]) {
                    return false;
                }
            }
            return true;
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
        changeDbkeyOfSelected() {
            this.runOnSelection(changeDbkeyOfSelectedContent, { dbkey: this.selectedDbKey });
            this.selectedDbKey = "?";
        },
        changeDatatypeOfSelected() {
            this.runOnSelection(changeDatatypeOfSelectedContent, { datatype: this.selectedDatatype });
            this.selectedDatatype = "auto";
        },
        addTagsToSelected() {
            this.runOnSelection(addTagsToSelectedContent, { tags: this.selectedTags });
            this.selectedTags = [];
        },
        removeTagsFromSelected() {
            this.runOnSelection(removeTagsFromSelectedContent, { tags: this.selectedTags });
            this.selectedTags = [];
        },
        async runOnSelection(operation, extraParams = null) {
            this.$emit("update:operation-running", this.history.update_time);
            const items = this.getExplicitlySelectedItems();
            const filters = getQueryDict(this.filterText);
            this.$emit("update:show-selection", false);
            let expectHistoryUpdate = false;
            try {
                const result = await operation(this.history, filters, items, extraParams);
                expectHistoryUpdate = result.success_count > 0;
                if (result.errors.length) {
                    this.handleOperationError(null, result);
                }
            } catch (error) {
                this.handleOperationError(error, null);
            }
            if (!expectHistoryUpdate) {
                this.$emit("update:operation-running", null);
            }
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
        handleOperationError(errorMessage, result) {
            this.$emit("operation-error", { errorMessage, result });
        },
        onSelectedDbKey(dbkey) {
            this.selectedDbKey = dbkey.id;
        },
        onSelectedDatatype(datatype) {
            this.selectedDatatype = datatype.id;
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
