<template>
    <section>
        <b-dropdown
            no-caret
            size="sm"
            variant="link"
            class="rounded-0"
            toggle-class="text-decoration-none rounded-0"
            data-description="history action menu">
            <template v-slot:button-content>
                <Icon icon="cog" />
            </template>
            <b-dropdown-text id="history-op-all-content">
                <span v-localize>With entire history...</span>
            </b-dropdown-text>
            <b-dropdown-item v-if="history.contents_active.active" data-description="copy datasets" @click="onCopy">
                <span v-localize>Copy Datasets</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="history.contents_active.hidden" v-b-modal:show-all-hidden-content>
                <span v-localize>Unhide All Hidden Content</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="history.contents_active.hidden" v-b-modal:delete-all-hidden-content>
                <span v-localize>Delete All Hidden Content</span>
            </b-dropdown-item>
            <b-dropdown-item v-if="history.contents_active.deleted" v-b-modal:purge-all-deleted-content>
                <span v-localize>Purge All Deleted Content</span>
            </b-dropdown-item>
        </b-dropdown>

        <b-modal id="show-all-hidden-content" title="Show Hidden Datasets" title-tag="h2" @ok="unhideAll">
            <p v-localize>Really unhide all hidden datasets?</p>
        </b-modal>
        <b-modal id="delete-all-hidden-content" title="Delete Hidden Datasets" title-tag="h2" @ok="deleteAllHidden">
            <p v-localize>Really delete all hidden datasets?</p>
        </b-modal>
        <b-modal id="purge-all-deleted-content" title="Purge Deleted Datasets" title-tag="h2" @ok="purgeAllDeleted">
            <p v-localize>Really permanently delete all deleted datasets?</p>
            <p><strong v-localize class="text-danger">Warning, this operation cannot be undone.</strong></p>
        </b-modal>
    </section>
</template>

<script>
import { unhideAllHiddenContent, deleteAllHiddenContent, purgeAllDeletedContent } from "components/History/model/crud";
import { iframeRedirect } from "components/plugins/legacyNavigation";

export default {
    props: {
        history: { type: Object, required: true },
    },
    methods: {
        onCopy() {
            iframeRedirect("/dataset/copy_datasets");
        },
        unhideAll() {
            this.runOperation(() => unhideAllHiddenContent(this.history));
        },
        deleteAllHidden() {
            this.runOperation(() => deleteAllHiddenContent(this.history));
        },
        purgeAllDeleted() {
            this.runOperation(() => purgeAllDeletedContent(this.history));
        },
        async runOperation(operation) {
            this.$emit("update:operation-running", this.history.update_time);
            await operation();
            this.$emit("update:operation-running", this.history.update_time);
        },
    },
};
</script>
