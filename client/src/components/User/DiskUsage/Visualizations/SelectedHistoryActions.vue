<script setup lang="ts">
import { BButton } from "bootstrap-vue";
import { bytesToString } from "@/utils/utils";
import type { DataValuePoint } from "./Charts";
import { computed } from "vue";
import { faChartPie, faUndo, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";

interface SelectedHistoryActionsProps {
    data: DataValuePoint;
    isRecoverable: boolean;
}

const props = defineProps<SelectedHistoryActionsProps>();

//@ts-ignore bad library types
library.add(faChartPie, faUndo, faTrash);

const label = computed(() => props.data?.label ?? "No data");
const prettySize = computed(() => bytesToString(props.data?.value ?? 0));

const emit = defineEmits<{
    (e: "undelete-history", historyId: string): void;
    (e: "view-history", historyId: string): void;
    (e: "permanently-delete-history", historyId: string): void;
}>();

function onUndeleteHistory() {
    emit("undelete-history", props.data.id);
}

function onViewHistory() {
    emit("view-history", props.data.id);
}

function onPermanentlyDeleteHistory() {
    emit("permanently-delete-history", props.data.id);
}
</script>
<template>
    <div class="selected-history-info">
        <div class="h-md mx-2">
            <b>{{ label }}</b>
        </div>
        <div class="text-muted mx-2">
            Total storage space <b>{{ prettySize }}</b
            >.
            <span v-if="isRecoverable">
                This history was deleted. You can undelete it or permanently delete it to free up its storage space.
            </span>
        </div>

        <div class="my-2">
            <b-button
                variant="outline-primary"
                size="sm"
                class="mx-2"
                title="Visualize this history storage usage"
                @click="onViewHistory">
                <font-awesome-icon icon="chart-pie" />
            </b-button>
            <b-button
                v-if="isRecoverable"
                variant="outline-primary"
                size="sm"
                class="mx-2"
                title="Undelete this history"
                @click="onUndeleteHistory">
                <font-awesome-icon icon="undo" />
            </b-button>
            <b-button
                v-if="isRecoverable"
                variant="outline-danger"
                size="sm"
                class="mx-2"
                title="Permanently delete this history and its contents"
                @click="onPermanentlyDeleteHistory">
                <font-awesome-icon icon="trash" />
            </b-button>
        </div>
    </div>
</template>

<style scoped>
.selected-history-info {
    text-align: left;
    margin-top: 1rem;
    margin-bottom: 1rem;
    max-width: 400px;
}
</style>
