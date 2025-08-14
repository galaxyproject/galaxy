<template>
    <section v-if="hasSelection && !isMultiViewItem">
        <b-dropdown text="Selection" size="sm" variant="primary" data-description="selected content menu" no-flip>
            <template v-slot:button-content>
                <span v-if="selectionMatchesQuery" data-test-id="all-filter-selected">
                    {{ localize("All") }} <b>{{ totalItemsInQuery }}</b> {{ localize("selected") }}
                </span>
                <span v-else data-test-id="num-active-selected">
                    <b>{{ selectionSize }}</b> {{ localize("of") }} {{ totalItemsInQuery }} {{ localize("selected") }}
                </span>
            </template>
            <b-dropdown-text>
                <span data-description="selected count"
                    >{{ localize("With") }} {{ numSelected }} {{ localize("selected...") }}</span
                >
            </b-dropdown-text>
            <b-dropdown-item v-if="canUnhideSelection" data-description="unhide option" @click="unhideSelected">
                <span v-localize>Unhide</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="canHideSelection" data-description="hide option" @click="hideSelected">
                <span v-localize>Hide</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="canUndeleteSelection" data-description="undelete option" @click="undeleteSelected">
                <span v-localize>Undelete</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="canDeleteSelection" data-description="delete option" @click="deleteSelected">
                <span v-localize>Delete</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="canPurgeSelection" data-description="purge option" @click="purgeSelected">
                <span v-localize>Delete (permanently)</span>
            </b-dropdown-item>
            <b-dropdown-divider v-if="showBuildOptions" />
            <b-dropdown-divider v-if="showBuildOptionForAll" />
            <b-dropdown-item
                v-if="showBuildOptionForAll"
                data-description="build list all"
                @click="buildDatasetListAll">
                <span v-localize>Build Dataset List</span>
            </b-dropdown-item>
            <b-dropdown-divider />
            <b-dropdown-item data-description="change database build" @click="showChangeDbKeyModal = true">
                <span v-localize>Change Database/Build</span>
            </b-dropdown-item>
            <b-dropdown-item
                v-if="isConfigLoaded && config.enable_celery_tasks"
                data-description="change data type"
                @click="showChangeDatatypeModal = true">
                <span v-localize>Change data type</span>
            </b-dropdown-item>
            <b-dropdown-item data-description="add tags" @click="showAddTagsModal = true">
                <span v-localize>Add tags</span>
            </b-dropdown-item>
            <b-dropdown-item data-description="remove tags" @click="showRemoveTagsModal = true">
                <span v-localize>Remove tags</span>
            </b-dropdown-item>
            <b-dropdown-divider v-if="showBuildOptions" />
            <b-dropdown-item v-if="showBuildOptions" data-description="auto build list" @click="listWizard(false)">
                <span v-localize>Auto Build List</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="showBuildOptions" data-description="advanced build list" @click="listWizard(true)">
                <span v-localize>Advanced Build List</span>
            </b-dropdown-item>
        </b-dropdown>

        <GModal
            :show.sync="showChangeDbKeyModal"
            title="Change Database/Build?"
            confirm
            size="small"
            overflow-visible
            @ok="changeDbkeyOfSelected"
            @cancel="resetDbKey">
            <p v-localize>Select a new Database/Build for {{ numSelected }} items:</p>
            <DbKeyProvider v-slot="{ item: dbkeys, loading: loadingDbKeys }">
                <SingleItemSelector
                    collection-name="Database/Builds"
                    :loading="loadingDbKeys"
                    :items="dbkeys"
                    :current-item="selectedDbKey"
                    @update:selected-item="onSelectedDbKey" />
            </DbKeyProvider>
        </GModal>
        <GModal
            :show.sync="showChangeDatatypeModal"
            title="Change data type?"
            confirm
            size="small"
            overflow-visible
            :ok-disabled="selectedDatatype == null"
            @ok="changeDatatypeOfSelected"
            @cancel="resetDatatype">
            <p v-localize>Select a new data type for {{ numSelected }} items:</p>
            <DatatypesProvider v-slot="{ item: datatypes, loading: loadingDatatypes }">
                <SingleItemSelector
                    collection-name="Data Types"
                    :loading="loadingDatatypes"
                    :items="datatypes"
                    :current-item="selectedDatatype"
                    @update:selected-item="onSelectedDatatype" />
            </DatatypesProvider>
        </GModal>
        <GModal
            :show.sync="showAddTagsModal"
            title="Add tags?"
            confirm
            size="small"
            :ok-disabled="noTagsSelected"
            @ok="addTagsToSelected"
            @cancel="selectedTags = []">
            <p v-localize>Apply the following tags to {{ numSelected }} items:</p>
            <StatelessTags :key="showAddTagsModal" v-model="selectedTags" class="tags" />
            <GTip class="mt-2" :tips="['Press Enter after typing each tag.']" />
        </GModal>
        <GModal
            :show.sync="showRemoveTagsModal"
            title="Remove tags?"
            confirm
            size="small"
            :ok-disabled="noTagsSelected"
            @ok="removeTagsFromSelected"
            @cancel="selectedTags = []">
            <p v-localize>Remove the following tags from {{ numSelected }} items:</p>
            <StatelessTags :key="showRemoveTagsModal" v-model="selectedTags" class="tags" />
            <GTip :tips="['Press Enter after typing each tag.']" />
        </GModal>
        <CollectionCreatorIndex
            v-if="collectionModalType"
            v-model:show="collectionModalShow"
            :history-id="history.id"
            :collection-type="collectionModalType"
            :file-sources-configured="config.file_sources_configured"
            :filter-text="filterText"
            :selected-items="collectionSelection"
            hide-on-create
            default-hide-source-items
            @created-collection="createdCollection" />
    </section>
</template>

<script>
import { ref } from "vue";

import { HistoryFilters } from "@/components/History/HistoryFilters";
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
} from "@/components/History/model/crud";
import { DatatypesProvider, DbKeyProvider } from "@/components/providers";
import { StatelessTags } from "@/components/Tags";
import { useConfig } from "@/composables/config";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useCollectionBuilderItemSelection } from "@/stores/collectionBuilderItemsStore";

import GModal from "@/components/BaseComponents/GModal.vue";
import GTip from "@/components/BaseComponents/GTip.vue";
import CollectionCreatorIndex from "@/components/Collections/CollectionCreatorIndex.vue";
import SingleItemSelector from "@/components/SingleItemSelector.vue";

export default {
    components: {
        CollectionCreatorIndex,
        DbKeyProvider,
        DatatypesProvider,
        GModal,
        GTip,
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
        const { confirm } = useConfirmDialog();

        // Modals for selection operations
        const showChangeDbKeyModal = ref(false);
        const showChangeDatatypeModal = ref(false);
        const showAddTagsModal = ref(false);
        const showRemoveTagsModal = ref(false);

        const selectedDbKey = ref({ id: "?", text: "unspecified (?)" });
        const selectedDatatype = ref({ id: "auto", text: "Auto-detect" });

        function resetDbKey() {
            selectedDbKey.value = { id: "?", text: "unspecified (?)" };
        }
        function resetDatatype() {
            selectedDatatype.value = { id: "auto", text: "Auto-detect" };
        }

        return {
            config,
            confirm,
            isConfigLoaded,
            showChangeDbKeyModal,
            showChangeDatatypeModal,
            showAddTagsModal,
            showRemoveTagsModal,
            selectedDbKey,
            selectedDatatype,
            resetDbKey,
            resetDatatype,
        };
    },
    data: function () {
        return {
            collectionModalShow: false,
            collectionModalType: null,
            collectionSelection: undefined,
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
        canPurgeSelection() {
            return this.contentSelection.size === 0 || this.isQuerySelection || !this.areAllSelectedPurged;
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
        listWizard(advanced) {
            const { setSelectedItems } = useCollectionBuilderItemSelection();
            const selection = Array.from(this.contentSelection.values());
            setSelectedItems(this.history.id, selection);

            if (this.$route.path === "/collection/new_list") {
                // vue-router 4 supports a native force push with clean URLs, but we're using a __vkey__
                // bit as a workaround to allow the builder to be invoked consecutively
                this.$router.push({ path: `/collection/new_list?advanced=${advanced}` }, { force: true });
            } else {
                this.$router.push(`/collection/new_list?advanced=${advanced}`);
            }
        },
        // Selected content manipulation, hide/show/delete/purge (using the confirm dialog)
        async confirmAndRun(operation, message, options = {}) {
            if (await this.confirm(message, options)) {
                this.runOnSelection(operation);
            }
        },
        hideSelected() {
            return this.confirmAndRun(hideSelectedContent, `Really hide ${this.numSelected} content items?`, {
                title: "Hide Selected Content?",
                okText: "Hide",
            });
        },
        unhideSelected() {
            return this.confirmAndRun(unhideSelectedContent, `Really show ${this.numSelected} content items?`, {
                title: "Show Selected Content?",
                okText: "Show",
            });
        },
        deleteSelected() {
            return this.confirmAndRun(deleteSelectedContent, `Really delete ${this.numSelected} content items?`, {
                title: "Delete Selected Content?",
                okText: "Delete",
                okColor: "red",
            });
        },
        undeleteSelected() {
            return this.confirmAndRun(undeleteSelectedContent, `Really restore ${this.numSelected} content items?`, {
                title: "Restore Selected Content?",
                okText: "Restore",
            });
        },
        purgeSelected() {
            return this.confirmAndRun(purgeSelectedContent, `Really purge ${this.numSelected} content items?`, {
                title: "Purge Selected Content?",
                okText: "Purge",
                okColor: "red",
            });
        },
        changeDbkeyOfSelected() {
            this.runOnSelection(changeDbkeyOfSelectedContent, { dbkey: this.selectedDbKey.id });
            this.resetDbKey();
        },
        changeDatatypeOfSelected() {
            this.runOnSelection(changeDatatypeOfSelectedContent, { datatype: this.selectedDatatype.id });
            this.resetDatatype();
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
        buildDatasetListAll() {
            this.collectionModalType = "list";
            this.collectionSelection = undefined;
            this.collectionModalShow = true;
        },
    },
};
</script>
