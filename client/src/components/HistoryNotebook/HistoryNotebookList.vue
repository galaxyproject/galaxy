<script setup lang="ts">
import { faChevronRight, faEye, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

import type { HistoryNotebookSummary } from "@/api/historyNotebooks";

defineProps<{
    notebooks: HistoryNotebookSummary[];
}>();

defineEmits<{
    (e: "select", notebookId: string): void;
    (e: "view", notebookId: string): void;
    (e: "create"): void;
}>();

function getNotebookTitle(notebook: HistoryNotebookSummary): string {
    return notebook.title || "Untitled Notebook";
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
            <h4 class="mb-0">Notebooks</h4>
            <BButton variant="primary" size="sm" data-description="create notebook button" @click="$emit('create')">
                <FontAwesomeIcon :icon="faPlus" />
                New Notebook
            </BButton>
        </div>

        <div v-if="notebooks.length === 0" class="empty-state text-center p-4" data-description="notebook empty state">
            <p class="text-muted">No notebooks yet</p>
            <p class="text-muted small">
                Create a notebook to document your analysis with rich markdown, embedded datasets, and visualizations.
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
