<script setup lang="ts">
import { bytesToString } from "@/utils/utils";
import type { DataValuePoint } from "./Charts";
import { computed } from "vue";

interface SelectedHistoryActionsProps {
    data: DataValuePoint;
    isRecoverable: boolean;
}

const props = defineProps<SelectedHistoryActionsProps>();

const label = computed(() => props.data?.label ?? "No data");
const prettySize = computed(() => bytesToString(props.data?.value ?? 0));
</script>
<template>
    <div class="selected-history-info">
        <div class="h-md mx-2">
            <b>{{ label }}</b>
        </div>
        <div class="text-muted mx-2">Total storage space {{ prettySize }}</div>

        <div class="my-2">
            <b-button v-if="!isRecoverable" variant="outline-primary" size="sm" class="mx-2">
                Switch to this history
            </b-button>
            <b-button variant="outline-primary" size="sm" class="mx-2"> View this history </b-button>
        </div>

        <div v-if="isRecoverable">
            <p class="text-muted text-justify mx-2">
                This history was deleted. You can recover it or permanently delete it to free up
                <b>{{ prettySize }}</b> of storage space.
            </p>
            <b-button variant="outline-primary" size="sm" class="mx-2" title="Recover this history">
                Undelete
            </b-button>
            <b-button variant="outline-danger" size="sm" class="mx-2"> Permanently delete this history </b-button>
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
