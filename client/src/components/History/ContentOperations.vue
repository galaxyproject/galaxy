<template>
    <section>
        <nav class="content-operations-menu d-flex justify-content-between bg-secondary">
            <b-button-group>
                <IconButton
                    :title="hasSelection ? 'Select All Contents' : 'Unselect All Contents'"
                    icon="check-square"
                    :disabled="!totalMatches"
                    :pressed="hasSelection"
                    @click="toggleSelectAll" />
                <IconButton
                    title="Filter History Content"
                    icon="filter"
                    :disabled="!totalMatches"
                    :pressed="showFilter"
                    @click="showFilter = !showFilter"
                    data-description="content filter toggle" />
                <IconButton
                    title="Collapse Expanded Items"
                    icon="compress"
                    :disabled="!expandedCount"
                    @click="$emit('collapseAllContent')" />
            </b-button-group>

            <b-button-group>
                <b-dropdown
                    class="history-contents-list-action-menu-btn"
                    size="sm"
                    text="Selection"
                    :disabled="!hasSelection"
                    data-description="selected content menu">
                    <b-dropdown-text id="history-op-selected-content">
                        <span v-localize v-if="hasSelection">With {{ numSelected }} selected items...</span>
                        <span v-localize v-else>You don't have any selected content.</span>
                    </b-dropdown-text>

                    <b-dropdown-item aria-describedby="history-op-selected-content" v-b-modal:hide-selected-content>
                        <span v-localize>Hide</span>
                    </b-dropdown-item>

                    <b-dropdown-item aria-describedby="history-op-selected-content" v-b-modal:show-selected-content>
                        <span v-localize>Unhide</span>
                    </b-dropdown-item>

                    <b-dropdown-item aria-describedby="history-op-selected-content" v-b-modal:delete-selected-content>
                        <span v-localize>Delete</span>
                    </b-dropdown-item>

                    <b-dropdown-item aria-describedby="history-op-selected-content" v-b-modal:restore-selected-content>
                        <span v-localize>Undelete</span>
                    </b-dropdown-item>

                    <b-dropdown-item
                        aria-describedby="history-op-selected-content"
                        v-b-modal:purge-selected-content
                        :disabled="!hasSelection">
                        <span v-localize>Permanently Delete</span>
                    </b-dropdown-item>

                    <b-dropdown-item
                        aria-describedby="history-op-selected-content"
                        @click="buildDatasetList"
                        data-description="build list">
                        <span v-localize>Build Dataset List</span>
                    </b-dropdown-item>

                    <b-dropdown-item
                        aria-describedby="history-op-selected-content"
                        @click="buildDatasetPair"
                        data-description="build pair">
                        <span v-localize>Build Dataset Pair</span>
                    </b-dropdown-item>

                    <b-dropdown-item
                        aria-describedby="history-op-selected-content"
                        @click="buildListOfPairs"
                        data-description="build list of pairs">
                        <span v-localize>Build List of Dataset Pairs</span>
                    </b-dropdown-item>

                    <b-dropdown-item
                        aria-describedby="history-op-selected-content"
                        @click="buildCollectionFromRules"
                        data-description="build collection from rules">
                        <span v-localize>Build Collection from Rules</span>
                    </b-dropdown-item>
                </b-dropdown>

                <b-dropdown
                    class="history-contents-list-action-menu-btn"
                    size="sm"
                    text="History"
                    :disabled="!totalMatches"
                    data-description="history action menu">
                    <b-dropdown-text id="history-op-all-content">
                        <span v-localize>With entire history...</span>
                    </b-dropdown-text>

                    <b-dropdown-item
                        aria-describedby="history-op-all-content"
                        @click="iframeRedirect('/dataset/copy_datasets')"
                        data-description="copy datasets">
                        <span v-localize>Copy Datasets</span>
                    </b-dropdown-item>

                    <b-dropdown-item v-b-modal:show-all-hidden-content aria-describedby="history-op-all-content">
                        <span v-localize>Unhide All Hidden Content</span>
                    </b-dropdown-item>

                    <b-dropdown-item v-b-modal:delete-all-hidden-content aria-describedby="history-op-all-content">
                        <span v-localize>Delete All Hidden Content</span>
                    </b-dropdown-item>

                    <b-dropdown-item v-b-modal:purge-all-deleted-content aria-describedby="history-op-all-content">
                        <span v-localize>Purge All Hidden Content</span>
                    </b-dropdown-item>
                </b-dropdown>
            </b-button-group>
        </nav>

        <transition name="shutterfade">
            <content-filters v-if="showContentFilters" class="content-filters p-2" :params.sync="localParams" />
        </transition>

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
import { History } from "./model/History";
import {
    hideSelectedContent,
    unhideSelectedContent,
    deleteSelectedContent,
    undeleteSelectedContent,
    purgeSelectedContent,
    unhideAllHiddenContent,
    deleteAllHiddenContent,
    purgeAllDeletedContent,
} from "./model";
import { createDatasetCollection } from "./model/queries";
import { cacheContent } from "components/providers/History/caching";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import { buildCollectionModal } from "./adapters/buildCollectionModal";
import ContentFilters from "./ContentFilters";
import IconButton from "components/IconButton";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        ContentFilters,
        IconButton,
    },
    props: {
        history: { type: History, required: true },
        params: { type: Object, required: true },
        contentSelection: { type: Map, required: true },
        showSelection: { type: Boolean, required: true },
        totalMatches: { type: Number, required: true },
        expandedCount: { type: Number, required: false, default: 0 },
        debug: { type: Boolean, default: false },
    },
    data() {
        return {
            showFilter: false,
        };
    },
    computed: {
        showContentFilters() {
            const { showHidden, showDeleted, filterText } = this.params;
            return this.showFilter || showHidden || showDeleted || filterText;
        },

        localParams: {
            get() {
                return this.params;
            },
            set(newVal) {
                this.$emit("update:params", Object.assign({}, newVal));
                if (this.showContentFilters) {
                    this.$emit("reload");
                }
            },
        },

        numSelected() {
            return this.contentSelection.size || 0;
        },

        hasSelection() {
            return this.numSelected > 0;
        },

        countHidden() {
            return this.history.contents_active.hidden;
        },
    },
    methods: {
        toggleSelectAll() {
            if (this.hasSelection) {
                this.$emit("resetSelection");
                this.$emit("update:show-selection", false);
            } else {
                this.$emit("selectAllContent");
                this.$emit("update:show-selection", true);
            }
        },

        // History-wide bulk updates, does server query first to determine "selection"
        async unhideAll(evt) {
            await unhideAllHiddenContent(this.history);
            this.$emit("reload");
        },
        async deleteAllHidden(evt) {
            await deleteAllHiddenContent(this.history);
            this.$emit("reload");
        },
        async purgeAllDeleted(evt) {
            await purgeAllDeletedContent(this.history);
            this.$emit("reload");
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
            const items = Array.from(this.contentSelection.values());
            const type_ids = items.map((o) => o.type_id);
            const results = await fn(this.history, type_ids);
            if (this.debug) {
                console.log("operation results", results);
            }
            this.$emit("resetSelection");
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
            const newCollection = await createDatasetCollection(this.history, modalResult);

            // cache the collection
            await cacheContent(newCollection);

            // have to hide the source items if that was requested
            if (modalResult.hide_source_items) {
                this.contentSelection.forEach(async (dataset) => {
                    await cacheContent({ ...dataset, visible: false }, true);
                });
                this.$emit("resetSelection");
            }
        },
    },
    watch: {
        hasSelection(newVal) {
            if (newVal) {
                this.$emit("update:showSelection", true);
            }
        },
    },
};
</script>

<style lang="scss">
// remove borders around buttons in menu
.content-operations-menu .btn-group .btn {
    border-color: transparent !important;
}
</style>
