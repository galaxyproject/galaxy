<script setup lang="ts">
import { faChevronRight, faEye, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

import type { HistoryPageSummary } from "@/api/pages";
import { PAGE_LABELS } from "@/components/Page/constants";

defineProps<{
    pages: HistoryPageSummary[];
}>();

defineEmits<{
    (e: "select", pageId: string): void;
    (e: "view", pageId: string): void;
    (e: "create"): void;
}>();

const labels = PAGE_LABELS.history;

function getPageTitle(page: HistoryPageSummary): string {
    return page.title || labels.defaultTitle;
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
            <h4 class="mb-0">{{ labels.entityNamePlural }}</h4>
            <BButton variant="primary" size="sm" data-description="create page button" @click="$emit('create')">
                <FontAwesomeIcon :icon="faPlus" />
                {{ labels.newButton }}
            </BButton>
        </div>

        <div v-if="pages.length === 0" class="empty-state text-center p-4" data-description="page empty state">
            <p class="text-muted">{{ labels.emptyStateTitle }}</p>
            <p class="text-muted small">
                {{ labels.emptyStateDescription }}
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
                            :title="labels.viewButton"
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
