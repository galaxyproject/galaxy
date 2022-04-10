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
        <b-modal id="show-all-hidden-content" title="Show Hidden Datasets" title-tag="h2" @ok="unhideAll">
            <p v-localize>Really unhide all hidden datasets?</p>
        </b-modal>
        <b-modal id="delete-all-hidden-content" title="Delete Hidden Datasets" title-tag="h2" @ok="deleteAllHidden">
            <p v-localize>Really delete all hidden datasets?</p>
        </b-modal>
        <b-modal id="purge-all-deleted-content" title="Purge Deleted Datasets" title-tag="h2" @ok="purgeAllDeleted">
            <p v-localize>Really permanently delete all deleted datasets?</p>
            <p><strong class="text-danger" v-localize>Warning, this operation cannot be undone.</strong></p>
        </b-modal>
    </section>
</template>

<script>
import { unhideAllHiddenContent, deleteAllHiddenContent, purgeAllDeletedContent } from "components/History/model/crud";
import { iframeRedirect } from "components/plugins/legacyNavigation";
export default {
    props: {
        history: { type: Object, required: true },
        showSelection: { type: Boolean, required: true },
        hasMatches: { type: Boolean, required: true },
        expandedCount: { type: Number, required: false, default: 0 },
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
    },
};
</script>

<style lang="scss">
// remove borders around buttons in menu
.content-operations .btn-group .btn {
    border-color: transparent !important;
}
</style>
