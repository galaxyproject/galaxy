<script setup lang="ts">
import { faChevronRight, faEye, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

import type { HistoryPageSummary } from "@/api/pages";

defineProps<{
    pages: HistoryPageSummary[];
}>();

defineEmits<{
    (e: "select", pageId: string): void;
    (e: "view", pageId: string): void;
    (e: "create"): void;
}>();

function getPageTitle(page: HistoryPageSummary): string {
    return page.title || "Untitled Page";
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
    <div class="history-page-list" data-description="history page list">
        <div class="list-header d-flex justify-content-between align-items-center p-3 border-bottom">
            <h4 class="mb-0">Pages</h4>
            <BButton variant="primary" size="sm" data-description="create page button" @click="$emit('create')">
                <FontAwesomeIcon :icon="faPlus" />
                New Page
            </BButton>
        </div>

        <div v-if="pages.length === 0" class="empty-state text-center p-4" data-description="page empty state">
            <p class="text-muted">No pages yet</p>
            <p class="text-muted small">
                Create a page to document your analysis with rich markdown, embedded datasets, and visualizations.
            </p>
        </div>

        <div v-else class="page-items">
            <div
                v-for="page in pages"
                :key="page.id"
                class="page-item p-3 border-bottom cursor-pointer"
                data-description="page item"
                @click="$emit('select', page.id)">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="page-title fw-bold" data-description="page title">
                            {{ getPageTitle(page) }}
                        </div>
                        <div class="page-meta text-muted small">Updated {{ formatDate(page.update_time) }}</div>
                    </div>
                    <span class="page-actions d-flex align-items-center">
                        <BButton
                            variant="link"
                            size="sm"
                            class="p-1"
                            title="View page"
                            data-description="page view button"
                            @click.stop="$emit('view', page.id)">
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
.page-item:hover {
    background: var(--panel-header-bg);
}
.cursor-pointer {
    cursor: pointer;
}
</style>
