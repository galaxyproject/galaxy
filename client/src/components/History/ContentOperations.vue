<template>
    <section>
        <header class="d-flex align-items-center justify-content-between">
            <h6 class="text-nowrap mr-3">
                <span v-localize>Matches</span>
                <a href="#" @click="showFilter = !showFilter">
                    <span>{{ totalMatches }}</span>
                </a>
            </h6>

            <PriorityMenu style="max-width: 50%" :starting-height="27">
                <PriorityMenuItem
                    key="filter"
                    title="Filter History Content"
                    icon="fa fa-filter"
                    @click="showFilter = !showFilter"
                    :pressed="showFilter"
                />

                <PriorityMenuItem
                    key="selection"
                    title="Operations on multiple datasets"
                    icon="fas fa-check-square"
                    @click="$emit('update:show-selection', !showSelection)"
                    :pressed="showSelection"
                />

                <PriorityMenuItem
                    key="copy-datasets"
                    title="Copy Datasets"
                    icon="fas fa-copy"
                    @click="iframeRedirect('/dataset/copy_datasets')"
                />

                <PriorityMenuItem
                    key="collapse-expanded"
                    title="Collapse Expanded Datasets"
                    icon="fas fa-compress-alt"
                    @click="emit('collapseAllContent')"
                />

                <PriorityMenuItem
                    key="show-hidden-datasets"
                    title="Unhide All Hidden Datasets"
                    icon="fas fa-eye"
                    @click="$bvModal.show('show-hidden-content')"
                />

                <PriorityMenuItem
                    key="delete-hidden"
                    title="Delete Hidden Datasets"
                    icon="fas fa-trash"
                    @click="$bvModal.show('delete-hidden-content')"
                />

                <PriorityMenuItem
                    key="purge-hidden"
                    title="Purge Hidden Datasets"
                    icon="fas fa-burn"
                    @click="$bvModal.show('purge-deleted-content')"
                />
            </PriorityMenu>
        </header>

        <transition name="shutterfade">
            <content-filters v-if="showContentFilters" class="content-filters mt-1" :params.sync="localParams" />
        </transition>

        <transition name="shutterfade">
            <b-button-toolbar v-if="showSelection" class="content-selection justify-content-between mt-1">
                <b-button-group>
                    <b-button size="sm" @click="$emit('selectAllContent')">
                        {{ "Select All" | localize }}
                    </b-button>
                    <b-button size="sm" @click="$emit('resetSelection')">
                        {{ "Unselect All" | localize }}
                    </b-button>
                </b-button-group>

                <b-dropdown class="ml-auto" size="sm" text="With Selected" :disabled="!hasSelection">
                    <b-dropdown-item @click="hideSelected">
                        {{ "Hide Datasets" | localize }}
                    </b-dropdown-item>
                    <b-dropdown-item @click="unhideSelected">
                        {{ "Unhide Datasets" | localize }}
                    </b-dropdown-item>
                    <b-dropdown-item @click="deleteSelected">
                        {{ "Delete Datasets" | localize }}
                    </b-dropdown-item>
                    <b-dropdown-item @click="undeleteSelected">
                        {{ "Undelete Datasets" | localize }}
                    </b-dropdown-item>
                    <b-dropdown-item @click="purgeSelected">
                        {{ "Permanently Delete Datasets" | localize }}
                    </b-dropdown-item>
                    <b-dropdown-item @click="buildDatasetList">
                        {{ "Build Dataset List" | localize }}
                    </b-dropdown-item>
                    <b-dropdown-item @click="buildDatasetPair">
                        {{ "Build Dataset Pair" | localize }}
                    </b-dropdown-item>
                    <b-dropdown-item @click="buildListOfPairs">
                        {{ "Build List of Dataset Pairs" | localize }}
                    </b-dropdown-item>
                    <b-dropdown-item @click="buildCollectionFromRules">
                        {{ "Build Collection from Rules" | localize }}
                    </b-dropdown-item>
                </b-dropdown>
            </b-button-toolbar>
        </transition>

        <!-- #region Menus and popovers -->

        <b-modal id="show-hidden-content" title="Show Hidden Datasets" title-tag="h2" @ok="unhideAll">
            <p>{{ "Really unhide all hidden datasets?" | localize }}</p>
        </b-modal>

        <b-modal id="delete-hidden-content" title="Delete Hidden Datasets" title-tag="h2" @ok="deleteAllHidden">
            <p>{{ "Really delete all hidden datasets?" | localize }}</p>
        </b-modal>

        <b-modal id="purge-deleted-content" title="Purge Deleted Datasets" title-tag="h2" @ok="purgeAllDeleted">
            <p>{{ "Really delete all deleted datasets permanently? This cannot be undone." | localize }}</p>
        </b-modal>

        <!-- #endregion -->
    </section>
</template>

<script>
import { SearchParams } from "./model/SearchParams";
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
import { cacheContent } from "./caching";

import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import ContentFilters from "./ContentFilters";
import { PriorityMenu, PriorityMenuItem } from "components/PriorityMenu";
import { buildCollectionModal } from "./adapters/buildCollectionModal";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        ContentFilters,
        PriorityMenu,
        PriorityMenuItem,
    },
    props: {
        history: { type: History, required: true },
        params: { type: SearchParams, required: true },
        contentSelection: { type: Map, required: true },
        showSelection: { type: Boolean, required: true },
        totalMatches: { type: Number, required: true },
    },
    data() {
        return {
            showFilter: false,
        };
    },
    computed: {
        // pop it open if anything is selected
        showContentFilters() {
            const { showHidden, showDeleted, filterText } = this.params;
            return this.showFilter || showHidden || showDeleted || filterText;
        },

        // pass-through
        localParams: {
            get() {
                return this.params;
            },
            set(newVal) {
                this.$emit("update:params", newVal.clone());
            },
        },

        hasSelection() {
            return this.contentSelection.size > 0;
        },

        countHidden() {
            return this.history.contents_active.hidden;
        },
    },
    methods: {
        // #region history-wide bulk updates, does server query first to determine "selection"

        async unhideAll(evt) {
            await unhideAllHiddenContent(this.history);
            this.$emit("manualReload");
            evt.vueTarget.hide();
        },
        async deleteAllHidden(evt) {
            await deleteAllHiddenContent(this.history);
            this.$emit("manualReload");
            evt.vueTarget.hide();
        },
        async purgeAllDeleted(evt) {
            await purgeAllDeletedContent(this.history);
            this.$emit("manualReload");
            evt.vueTarget.hide();
        },

        // #endregion

        // #region Selected content manipulation, hide/show/delete/purge

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
            await fn(this.history, type_ids);
            this.$emit("resetSelection");
            this.$emit("manualReload");
        },

        // #endregion

        // #region collection creation, fires up a modal

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
            await cacheContent(newCollection);
            this.$emit("manualReload");
        },

        // #endregion
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
