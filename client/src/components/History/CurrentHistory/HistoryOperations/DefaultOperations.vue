<template>
    <section>
        <GDropdown
            no-caret
            size="sm"
            variant="link"
            class="rounded-0"
            toggle-class="text-decoration-none rounded-0"
            data-description="history action menu">
            <template v-slot:button-content>
                <span class="sr-only">History actions</span>
                <Icon icon="cog" />
            </template>
            <GDropdownText id="history-op-all-content">
                <span v-localize>With entire history...</span>
            </GDropdownText>
            <GDropdownItem data-description="copy datasets" @click="onCopy">
                <span v-localize>Copy Datasets</span>
            </GDropdownItem>
            <GDropdownItem v-if="numItemsHidden" v-b-modal:show-all-hidden-content>
                <span v-localize>Unhide All Hidden Content</span>
            </GDropdownItem>
            <GDropdownItem v-if="numItemsHidden" v-b-modal:delete-all-hidden-content>
                <span v-localize>Delete All Hidden Content</span>
            </GDropdownItem>
            <GDropdownItem v-if="numItemsDeleted" v-b-modal:purge-all-deleted-content>
                <span v-localize>Purge All Deleted Content</span>
            </GDropdownItem>
        </GDropdown>

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
import { deleteAllHiddenContent, purgeAllDeletedContent, unhideAllHiddenContent } from "components/History/model/crud";
import { iframeRedirect } from "components/plugins/legacyNavigation";

import { usesDetailedHistoryMixin } from "../usesDetailedHistoryMixin.js";

import GDropdown from "@/component-library/GDropdown.vue";
import GDropdownItem from "@/component-library/GDropdownItem.vue";
import GDropdownText from "@/component-library/GDropdownText.vue";

export default {
    components: {
        GDropdown,
        GDropdownItem,
        GDropdownText,
    },
    mixins: [usesDetailedHistoryMixin],
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
