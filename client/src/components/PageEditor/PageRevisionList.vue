<script setup lang="ts">
import { faSpinner, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

import type { PageRevisionSummary } from "@/api/pages";

import SidebarList from "@/components/Common/SidebarList.vue";

const props = defineProps<{
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

function revisionKey(rev: PageRevisionSummary): string {
    return rev.id;
}

function onSelect(rev: PageRevisionSummary) {
    emit("select", rev.id);
}
</script>

<template>
    <div class="page-revision-list" data-description="page revision list">
        <SidebarList
            :items="revisions"
            :is-loading="isLoading"
            loading-message="Loading revisions..."
            empty-message="No revisions found."
            :item-key="revisionKey"
            item-data-description="revision item"
            @select="onSelect">
            <template v-slot:item="{ item: rev, index }">
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
                    :disabled="props.isReverting"
                    @click.stop="emit('restore', rev.id)">
                    <FontAwesomeIcon :icon="props.isReverting ? faSpinner : faUndo" :spin="props.isReverting" />
                    Restore
                </BButton>
            </template>
        </SidebarList>
    </div>
</template>

<style scoped>
.page-revision-list {
    max-height: 100%;
    overflow-y: auto;
}
</style>
