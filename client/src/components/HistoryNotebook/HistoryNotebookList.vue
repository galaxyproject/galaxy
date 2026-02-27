<script setup lang="ts">
import { faChevronRight, faEye, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

import type { HistoryPageSummary } from "@/api/pages";

defineProps<{
    notebooks: HistoryPageSummary[];
}>();

defineEmits<{
    (e: "select", pageId: string): void;
    (e: "view", pageId: string): void;
    (e: "create"): void;
}>();

function getNotebookTitle(notebook: HistoryPageSummary): string {
    return notebook.title || "Untitled Page";
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
    <div class="history-notebook-list" data-description="history notebook list">
        <div class="list-header d-flex justify-content-between align-items-center p-3 border-bottom">
            <h4 class="mb-0">Pages</h4>
            <BButton variant="primary" size="sm" data-description="create page button" @click="$emit('create')">
                <FontAwesomeIcon :icon="faPlus" />
                New Page
            </BButton>
        </div>

        <div v-if="notebooks.length === 0" class="empty-state text-center p-4" data-description="page empty state">
            <p class="text-muted">No pages yet</p>
            <p class="text-muted small">
                Create a page to document your analysis with rich markdown, embedded datasets, and visualizations.
            </p>
        </div>

        <div v-else class="notebook-items">
            <div
                v-for="notebook in notebooks"
                :key="notebook.id"
                class="notebook-item p-3 border-bottom cursor-pointer"
                data-description="notebook item"
                @click="$emit('select', notebook.id)">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="notebook-title fw-bold" data-description="notebook title">
                            {{ getNotebookTitle(notebook) }}
                        </div>
                        <div class="notebook-meta text-muted small">Updated {{ formatDate(notebook.update_time) }}</div>
                    </div>
                    <span class="notebook-actions d-flex align-items-center">
                        <BButton
                            variant="link"
                            size="sm"
                            class="p-1"
                            title="View notebook"
                            data-description="notebook view button"
                            @click.stop="$emit('view', notebook.id)">
                            <FontAwesomeIcon :icon="faEye" />
                        </BButton>
                        <FontAwesomeIcon :icon="faChevronRight" class="text-muted" />
                    </span>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.notebook-item:hover {
    background: var(--panel-header-bg);
}
.cursor-pointer {
    cursor: pointer;
}
</style>
