<script setup lang="ts">
import { BButton } from "bootstrap-vue";
import { bytesToString } from "@/utils/utils";
import localize from "@/utils/localization";
import type { DataValuePoint } from "./Charts";
import { computed } from "vue";
import { faChartBar, faUndo, faTrash, faInfoCircle, faArchive } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";

type ItemTypes = "history" | "dataset";

interface SelectedItemActionsProps {
    data: DataValuePoint;
    isRecoverable: boolean;
    itemType: ItemTypes;
    isArchived?: boolean;
}

const props = withDefaults(defineProps<SelectedItemActionsProps>(), {
    isArchived: false,
});

library.add(faChartBar, faUndo, faTrash, faInfoCircle, faArchive);

const label = computed(() => props.data?.label ?? "No data");
const prettySize = computed(() => bytesToString(props.data?.value ?? 0));
const viewDetailsIcon = computed(() => (props.itemType === "history" ? "chart-bar" : "info-circle"));

const emit = defineEmits<{
    (e: "view-item", itemId: string): void;
    (e: "undelete-item", itemId: string): void;
    (e: "permanently-delete-item", itemId: string): void;
}>();

function onUndeleteItem() {
    emit("undelete-item", props.data.id);
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
            <b-button
                variant="outline-primary"
                size="sm"
                class="mx-2"
                :title="localize(`Go to the details of this ${itemType}`)"
                @click="onViewItem">
                <font-awesome-icon :icon="viewDetailsIcon" />
            </b-button>
            <b-button
                v-if="isRecoverable"
                variant="outline-primary"
                size="sm"
                class="mx-2"
                :title="localize(`Undelete this ${itemType}`)"
                @click="onUndeleteItem">
                <font-awesome-icon icon="undo" />
            </b-button>
            <b-button
                v-if="isRecoverable"
                variant="outline-danger"
                size="sm"
                class="mx-2"
                :title="localize(`Permanently delete this ${itemType}`)"
                @click="onPermanentlyDeleteItem">
                <font-awesome-icon icon="trash" />
            </b-button>
        </div>
    </div>
</template>
