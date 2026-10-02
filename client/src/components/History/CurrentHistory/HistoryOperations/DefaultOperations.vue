<script setup lang="ts">
import { faBurn, faCog, faEyeSlash, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { toRef } from "vue";

import type { HistorySummaryExtended } from "@/api";
import {
    deleteAllHiddenContent,
    purgeAllDeletedContent,
    unhideAllHiddenContent,
} from "@/components/History/model/crud";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useHistoryContentStats } from "@/composables/historyContentStats";

import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";

interface Props {
    history: HistorySummaryExtended;
}

const props = defineProps<Props>();

const emit = defineEmits(["update:operation-running"]);

const { confirm } = useConfirmDialog();

const { numItemsDeleted, numItemsHidden } = useHistoryContentStats(toRef(props, "history"));

async function unhideAll() {
    const confirmed = await confirm("Really unhide all hidden datasets?", {
        title: "Show Hidden Datasets",
        okText: "Unhide",
        okIcon: faEyeSlash,
    });
    if (confirmed) {
        runOperation(() => unhideAllHiddenContent(props.history));
    }
}

async function deleteAllHidden() {
    const confirmed = await confirm("Really delete all hidden datasets?", {
        title: "Delete Hidden Datasets",
        okText: "Delete",
        okIcon: faTrash,
        okColor: "red",
    });
    if (confirmed) {
        runOperation(() => deleteAllHiddenContent(props.history));
    }
}

async function purgeAllDeleted() {
    const confirmed = await confirm(
        "Really permanently delete all deleted datasets? Warning, this operation cannot be undone.",
        {
            title: "Permanently Delete Deleted Datasets",
            okText: "Purge",
            okIcon: faBurn,
            okColor: "red",
        },
    );

    if (confirmed) {
        runOperation(() => purgeAllDeletedContent(props.history));
    }
}

async function runOperation(operation: () => Promise<unknown>) {
    emit("update:operation-running", props.history.update_time);
    await operation();
    emit("update:operation-running", props.history.update_time);
}
</script>

<template>
    <section v-if="numItemsHidden || numItemsHidden || numItemsDeleted">
        <GDropdown
            v-g-tooltip.hover
            no-caret
            size="sm"
            variant="link"
            class="rounded-0"
            title="Operations"
            toggle-class="text-decoration-none rounded-0"
            data-description="history action menu">
            <template v-slot:button-content>
                <span class="sr-only">History actions</span>

                <FontAwesomeIcon :icon="faCog" />
            </template>

            <GDropdownItem v-if="numItemsHidden" @click="unhideAll">
                <FontAwesomeIcon :icon="faEyeSlash" />
                <span v-localize>Unhide All Hidden Content</span>
            </GDropdownItem>

            <GDropdownItem v-if="numItemsHidden" @click="deleteAllHidden">
                <FontAwesomeIcon :icon="faTrash" />
                <span v-localize>Delete All Hidden Content</span>
            </GDropdownItem>

            <GDropdownItem v-if="numItemsDeleted" @click="purgeAllDeleted">
                <FontAwesomeIcon :icon="faBurn" />
                <span v-localize>Purge All Deleted Content</span>
            </GDropdownItem>
        </GDropdown>
    </section>
</template>
