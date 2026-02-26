<script setup lang="ts">
import { faSpinner, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

import type { PageRevisionSummary } from "@/api/historyPages";

defineProps<{
    revisions: PageRevisionSummary[];
    isLoading: boolean;
    isReverting: boolean;
}>();

const emit = defineEmits<{
    (e: "select", revisionId: string): void;
    (e: "restore", revisionId: string): void;
}>();

const SOURCE_LABELS: Record<string, string> = {
    user: "Manual",
    agent: "AI",
    restore: "Restored",
};

function sourceLabel(editSource: string | null | undefined): string {
    return SOURCE_LABELS[editSource || ""] || editSource || "Unknown";
}

function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}
</script>

<template>
    <div class="notebook-revision-list" data-description="notebook revision list">
        <div v-if="isLoading" class="text-center p-3" data-description="revision list loading">
            <FontAwesomeIcon :icon="faSpinner" spin />
            Loading revisions...
        </div>
        <div v-else-if="revisions.length === 0" class="text-muted p-3 text-center">No revisions found.</div>
        <div v-else class="revision-items">
            <div
                v-for="(rev, index) in revisions"
                :key="rev.id"
                class="revision-item d-flex align-items-center p-2 border-bottom"
                data-description="revision item"
                role="button"
                tabindex="0"
                @click="emit('select', rev.id)"
                @keydown.enter="emit('select', rev.id)">
                <div class="flex-grow-1">
                    <div class="small">
                        <span class="font-weight-bold">{{ formatDate(rev.create_time) }}</span>
                        <span class="text-muted ml-1">({{ sourceLabel(rev.edit_source) }})</span>
                        <span v-if="index === 0" class="badge badge-primary ml-1">Current</span>
                    </div>
                </div>
                <BButton
                    v-if="index > 0"
                    variant="outline-primary"
                    size="sm"
                    data-description="restore revision button"
                    :disabled="isReverting"
                    @click.stop="emit('restore', rev.id)">
                    <FontAwesomeIcon :icon="isReverting ? faSpinner : faUndo" :spin="isReverting" />
                    Restore
                </BButton>
            </div>
        </div>
    </div>
</template>

<style scoped>
.revision-item:hover {
    background: var(--gray-200);
    cursor: pointer;
}
.notebook-revision-list {
    max-height: 100%;
    overflow-y: auto;
}
</style>
