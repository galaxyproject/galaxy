<template>
    <section v-if="hasSelection && !isMultiViewItem">
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
            <b-dropdown-item v-if="canUnhideSelection" v-b-modal:show-selected-content data-description="unhide option">
                <span v-localize>Unhide</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="canHideSelection" v-b-modal:hide-selected-content data-description="hide option">
                <span v-localize>Hide</span>
            </b-dropdown-item>
            <b-dropdown-item
                v-if="canUndeleteSelection"
                v-b-modal:restore-selected-content
                data-description="undelete option">
                <span v-localize>Undelete</span>
            </b-dropdown-item>
            <b-dropdown-item
                v-if="canDeleteSelection"
                v-b-modal:delete-selected-content
                data-description="delete option">
                <span v-localize>Delete</span>
            </b-dropdown-item>
            <b-dropdown-item v-b-modal:purge-selected-content data-description="purge option">
                <span v-localize>Delete (permanently)</span>
            </b-dropdown-item>
            <b-dropdown-divider v-if="showBuildOptions" />
            <b-dropdown-item v-if="showBuildOptions" data-description="build list" @click="buildDatasetList">
                <span v-localize>Build Dataset List</span>
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
            <b-dropdown-divider v-if="showBuildOptionForAll" />
            <b-dropdown-item
                v-if="showBuildOptionForAll"
                data-description="build list all"
                @click="buildDatasetListAll">
                <span v-localize>Build Dataset List</span>
            </b-dropdown-item>
            <b-dropdown-divider />
            <b-dropdown-item v-b-modal:change-dbkey-of-selected-content data-description="change database build">
                <span v-localize>Change Database/Build</span>
            </b-dropdown-item>
            <b-dropdown-item
                v-if="isConfigLoaded && config.enable_celery_tasks"
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
            body-class="modal-with-selector"
            @ok="changeDbkeyOfSelected">
            <p v-localize>Select a new Database/Build for {{ numSelected }} items:</p>
            <DbKeyProvider v-slot="{ item: dbkeys, loading: loadingDbKeys }">
                <SingleItemSelector
                    collection-name="Database/Builds"
                    :loading="loadingDbKeys"
                    :items="dbkeys"
                    :current-item="selectedDbKey"
                    @update:selected-item="onSelectedDbKey" />
            </DbKeyProvider>
        </b-modal>
        <b-modal
            id="change-datatype-of-selected-content"
            title="Change data type?"
            title-tag="h2"
            body-class="modal-with-selector"
            :ok-disabled="selectedDatatype == null"
            @ok="changeDatatypeOfSelected">
            <p v-localize>Select a new data type for {{ numSelected }} items:</p>
            <DatatypesProvider v-slot="{ item: datatypes, loading: loadingDatatypes }">
                <SingleItemSelector
                    collection-name="Data Types"
                    :loading="loadingDatatypes"
                    :items="datatypes"
                    :current-item="selectedDatatype"
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
        <CollectionCreatorModal
            v-if="collectionModalType"
            :history-id="history.id"
            :collection-type="collectionModalType"
            :filter-text="filterText"
            :selected-items="collectionSelection"
            :show-modal.sync="collectionModalShow"
            default-hide-source-items
            @created-collection="createdCollection" />
    </section>
</template>

<script>
import { HistoryFilters } from "components/History/HistoryFilters";
import {
    addTagsToSelectedContent,
    changeDatatypeOfSelectedContent,
    changeDbkeyOfSelectedContent,
    deleteSelectedContent,
    hideSelectedContent,
    purgeSelectedContent,
    removeTagsFromSelectedContent,
    undeleteSelectedContent,
    unhideSelectedContent,
} from "components/History/model/crud";
import { DatatypesProvider, DbKeyProvider } from "components/providers";
import SingleItemSelector from "components/SingleItemSelector";
import { StatelessTags } from "components/Tags";

import { createDatasetCollection } from "@/components/History/model/queries";
import { useConfig } from "@/composables/config";

import { buildRuleCollectionModal } from "../../adapters/buildCollectionModal";

import CollectionCreatorModal from "@/components/Collections/CollectionCreatorModal.vue";

export default {
    components: {
        CollectionCreatorModal,
        DbKeyProvider,
        DatatypesProvider,
        SingleItemSelector,
        StatelessTags,
    },
    props: {
        history: { type: Object, required: true },
        filterText: { type: String, required: true },
        contentSelection: { type: Map, required: true },
        selectionSize: { type: Number, required: true },
        isQuerySelection: { type: Boolean, required: true },
        isMultiViewItem: { type: Boolean, required: true },
        totalItemsInQuery: { type: Number, default: 0 },
    },
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        return { config, isConfigLoaded };
    },
    data: function () {
        return {
            collectionModalShow: false,
            collectionModalType: null,
            collectionSelection: undefined,
            selectedDbKey: { id: "?", text: "unspecified (?)" },
            selectedDatatype: { id: "auto", text: "Auto-detect" },
            selectedTags: [],
        };
    },
    computed: {
        /** @returns {Boolean} */
        canUnhideSelection() {
            return this.areAllSelectedHidden || (this.isAnyVisibilityAllowed && !this.areAllSelectedVisible);
        },
        /** @returns {Boolean} */
        canHideSelection() {
            return this.areAllSelectedVisible || (this.isAnyVisibilityAllowed && !this.areAllSelectedHidden);
        },
        /** @returns {Boolean} */
        showDeleted() {
            return !HistoryFilters.checkFilter(this.filterText, "deleted", false);
        },
        /** @returns {Boolean} */
        canDeleteSelection() {
            return this.areAllSelectedActive || (this.isAnyDeletedStateAllowed && !this.areAllSelectedDeleted);
        },
        /** @returns {Boolean} */
        canUndeleteSelection() {
            return this.showDeleted && (this.isQuerySelection || !this.areAllSelectedPurged);
        },
        /** @returns {Boolean} */
        showBuildOptions() {
            return !this.isQuerySelection && this.areAllSelectedActive && !this.showDeleted;
        },
        /** @returns {Boolean} */
        showBuildOptionForAll() {
            return !this.showBuildOptions && this.selectionMatchesQuery;
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
        areAllSelectedPurged() {
            for (const item of this.contentSelection.values()) {
                if (Object.prototype.hasOwnProperty.call(item, "purged") && !item["purged"]) {
                    return false;
                }
            }
            return true;
        },
        areAllSelectedVisible() {
            for (const item of this.contentSelection.values()) {
                if (Object.prototype.hasOwnProperty.call(item, "visible") && !item["visible"]) {
                    return false;
                }
            }
            return true;
        },
        areAllSelectedHidden() {
            for (const item of this.contentSelection.values()) {
                if (Object.prototype.hasOwnProperty.call(item, "visible") && item["visible"]) {
                    return false;
                }
            }
            return true;
        },
        areAllSelectedActive() {
            for (const item of this.contentSelection.values()) {
                if (Object.prototype.hasOwnProperty.call(item, "deleted") && item["deleted"]) {
                    return false;
                }
            }
            return true;
        },
        areAllSelectedDeleted() {
            for (const item of this.contentSelection.values()) {
                if (Object.prototype.hasOwnProperty.call(item, "deleted") && !item["deleted"]) {
                    return false;
                }
            }
            return true;
        },
        isAnyVisibilityAllowed() {
            return HistoryFilters.checkFilter(this.filterText, "visible", "any");
        },
        isAnyDeletedStateAllowed() {
            return HistoryFilters.checkFilter(this.filterText, "deleted", "any");
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
            this.runOnSelection(changeDbkeyOfSelectedContent, { dbkey: this.selectedDbKey.id });
            this.selectedDbKey = { id: "?" };
        },
        changeDatatypeOfSelected() {
            this.runOnSelection(changeDatatypeOfSelectedContent, { datatype: this.selectedDatatype.id });
            this.selectedDatatype = { id: "auto", text: "Auto-detect" };
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
            const filters = HistoryFilters.getQueryDict(this.filterText);
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
            this.selectedDbKey = dbkey;
        },
        onSelectedDatatype(datatype) {
            this.selectedDatatype = datatype;
        },

        // collection creation, fires up a modal
        buildDatasetList() {
            this.collectionModalType = "list";
            this.collectionSelection = Array.from(this.contentSelection.values());
            this.collectionModalShow = true;
        },
        buildDatasetListAll() {
            this.collectionModalType = "list";
            this.collectionSelection = undefined;
            this.collectionModalShow = true;
        },
        buildListOfPairs() {
            this.collectionModalType = "list:paired";
            this.collectionSelection = Array.from(this.contentSelection.values());
            this.collectionModalShow = true;
        },
        createdCollection(collection) {
            this.$emit("reset-selection");
        },
        async buildCollectionFromRules() {
            const modalResult = await buildRuleCollectionModal(this.contentSelection, this.history.id);
            await createDatasetCollection(this.history, modalResult);

            // have to hide the source items if that was requested
            if (modalResult.hide_source_items) {
                this.$emit("hide-selection", this.contentSelection);
            }
            this.$emit("reset-selection");
        },
    },
};
</script>

<style>
.modal-with-selector {
    overflow: initial;
}
</style>
