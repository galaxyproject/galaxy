<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCog } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItem, BDropdownText, BModal } from "bootstrap-vue";
import { toRef } from "vue";

import { type HistorySummaryExtended } from "@/api";
import {
    deleteAllHiddenContent,
    purgeAllDeletedContent,
    unhideAllHiddenContent,
} from "@/components/History/model/crud";
import { iframeRedirect } from "@/components/plugins/legacyNavigation";
import { useHistoryContentStats } from "@/composables/historyContentStats";

library.add(faCog);

interface Props {
    history: HistorySummaryExtended;
}

const props = defineProps<Props>();

const emit = defineEmits(["update:operation-running"]);

const { numItemsDeleted, numItemsHidden } = useHistoryContentStats(toRef(props, "history"));

function onCopy() {
    iframeRedirect("/dataset/copy_datasets");
}

function unhideAll() {
    runOperation(() => unhideAllHiddenContent(props.history));
}

function deleteAllHidden() {
    runOperation(() => deleteAllHiddenContent(props.history));
}

function purgeAllDeleted() {
    runOperation(() => purgeAllDeletedContent(props.history));
}

async function runOperation(operation: () => Promise<unknown>) {
    emit("update:operation-running", props.history.update_time);
    await operation();
    emit("update:operation-running", props.history.update_time);
}
</script>

<template>
    <section>
        <BDropdown
            no-caret
            size="sm"
            variant="link"
            class="rounded-0"
            toggle-class="text-decoration-none rounded-0"
            data-description="history action menu">
            <template v-slot:button-content>
                <span class="sr-only">History actions</span>

                <FontAwesomeIcon :icon="faCog" />
            </template>

            <BDropdownText id="history-op-all-content">
                <span v-localize>With entire history...</span>
            </BDropdownText>

            <BDropdownItem data-description="copy datasets" @click="onCopy">
                <span v-localize>Copy Datasets</span>
            </BDropdownItem>

            <BDropdownItem v-if="numItemsHidden" v-b-modal:show-all-hidden-content>
                <span v-localize>Unhide All Hidden Content</span>
            </BDropdownItem>

            <BDropdownItem v-if="numItemsHidden" v-b-modal:delete-all-hidden-content>
                <span v-localize>Delete All Hidden Content</span>
            </BDropdownItem>

            <BDropdownItem v-if="numItemsDeleted" v-b-modal:purge-all-deleted-content>
                <span v-localize>Purge All Deleted Content</span>
            </BDropdownItem>
        </BDropdown>

        <BModal id="show-all-hidden-content" title="Show Hidden Datasets" title-tag="h2" @ok="unhideAll">
            <p v-localize>Really unhide all hidden datasets?</p>
        </BModal>

        <BModal id="delete-all-hidden-content" title="Delete Hidden Datasets" title-tag="h2" @ok="deleteAllHidden">
            <p v-localize>Really delete all hidden datasets?</p>
        </BModal>

        <BModal id="purge-all-deleted-content" title="Purge Deleted Datasets" title-tag="h2" @ok="purgeAllDeleted">
            <p v-localize>Really permanently delete all deleted datasets?</p>

            <p><strong v-localize class="text-danger">Warning, this operation cannot be undone.</strong></p>
        </BModal>
    </section>
</template>
