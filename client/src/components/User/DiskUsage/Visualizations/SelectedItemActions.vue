<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faArchive,
    faChartBar,
    faInfoCircle,
    faLocationArrow,
    faTrash,
    faUndo,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { bytesToString } from "@/utils/utils";

import type { DataValuePoint } from "./Charts";

type ItemTypes = "history" | "dataset";

interface SelectedItemActionsProps {
    data: DataValuePoint;
    isRecoverable: boolean;
    itemType: ItemTypes;
    isArchived?: boolean;
    canEdit?: boolean;
}

const { currentHistoryId } = useHistoryStore();

const props = withDefaults(defineProps<SelectedItemActionsProps>(), {
    isArchived: false,
    canEdit: false,
});

library.add(faArchive, faChartBar, faInfoCircle, faLocationArrow, faTrash, faUndo);

const label = computed(() => props.data?.label ?? "No data");
const prettySize = computed(() => bytesToString(props.data?.value ?? 0));
const viewDetailsIcon = computed(() => (props.itemType === "history" ? "chart-bar" : "info-circle"));
const canSetAsCurrent = computed(() => props.itemType === "history" && props.data.id !== currentHistoryId);

const emit = defineEmits<{
    (e: "set-current-history", historyId: string): void;
    (e: "view-item", itemId: string): void;
    (e: "undelete-item", itemId: string): void;
    (e: "permanently-delete-item", itemId: string): void;
}>();

function onUndeleteItem() {
    emit("undelete-item", props.data.id);
}

function onSetCurrentHistory() {
    emit("set-current-history", props.data.id);
}

function onViewItem() {
    emit("view-item", props.data.id);
}

function onPermanentlyDeleteItem() {
    emit("permanently-delete-item", props.data.id);
}
</script>
<template>
    <div class="selected-item-info">
        <div class="h-md mx-2">
            <b>{{ label }}</b>
        </div>
        <div class="text-muted mx-2">
            <span v-if="isArchived"><FontAwesomeIcon icon="archive" /> This {{ itemType }} is archived.</span><br />
            Total storage space taken: <b>{{ prettySize }}</b
            >.
            <span v-if="isRecoverable">
                This {{ itemType }} was deleted. You can <b>undelete</b> it or <b>permanently delete</b> it to free up
                its storage space.
            </span>
        </div>

        <div class="my-2">
            <BButton
                v-if="canSetAsCurrent"
                variant="outline-primary"
                size="sm"
                class="mx-2"
                :title="localize('Set this history as current')"
                @click="onSetCurrentHistory">
                <FontAwesomeIcon icon="location-arrow" />
            </BButton>
            <BButton
                variant="outline-primary"
                size="sm"
                class="mx-2"
                :title="localize(`Go to the details of this ${itemType}`)"
                @click="onViewItem">
                <FontAwesomeIcon :icon="viewDetailsIcon" />
            </BButton>
            <BButton
                v-if="isRecoverable && canEdit"
                variant="outline-primary"
                size="sm"
                class="mx-2"
                :title="localize(`Undelete this ${itemType}`)"
                @click="onUndeleteItem">
                <FontAwesomeIcon icon="undo" />
            </BButton>
            <BButton
                v-if="canEdit"
                variant="outline-danger"
                size="sm"
                class="mx-2"
                :title="localize(`Permanently delete this ${itemType}`)"
                @click="onPermanentlyDeleteItem">
                <FontAwesomeIcon icon="trash" />
            </BButton>
        </div>
    </div>
</template>
