<script setup lang="ts">
import { faArrowLeft, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, toRef } from "vue";

import type { HistoryPageSummary } from "@/api/pages";
import { PAGE_LABELS } from "@/components/Page/constants";
import { useHistoryBreadCrumbsTo } from "@/composables/historyBreadcrumbs";
import { useHistoryStore } from "@/stores/historyStore.js";
import { useUserStore } from "@/stores/userStore.js";

import BreadcrumbHeading from "../Common/BreadcrumbHeading.vue";
import Heading from "../Common/Heading.vue";
import PageCard from "./PageCard.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

const props = defineProps<{
    pages: HistoryPageSummary[];
    historyId: string;
    invocationId?: string;
}>();

const emit = defineEmits<{
    (e: "edit", pageId: string, username: string): void;
    (e: "view", pageId: string): void;
    (e: "create"): void;
    (e: "view-runtime-report"): void;
}>();

const historyStore = useHistoryStore();
const userStore = useUserStore();

const history = computed(() => historyStore.getHistoryById(props.historyId));

const unownedHistory = computed(() =>
    history.value && "user_id" in history.value
        ? !userStore.matchesCurrentUserId(history.value.user_id as string)
        : undefined,
);

const labels = computed(() => (props.invocationId ? PAGE_LABELS.invocation : PAGE_LABELS.history));

const { breadcrumbItems } = useHistoryBreadCrumbsTo(toRef(props, "historyId"), labels.value.entityNamePlural);
</script>

<template>
    <div class="d-flex flex-column" data-description="history page list">
        <BreadcrumbHeading v-if="!props.invocationId" :items="breadcrumbItems">
            <GButton
                class="text-nowrap"
                color="blue"
                size="small"
                data-description="create page button"
                @click="emit('create')">
                <FontAwesomeIcon :icon="faPlus" />
                {{ labels.newButton }}
            </GButton>
        </BreadcrumbHeading>
        <div v-else class="d-flex flex-gapx-1 pb-2">
            <Heading h1 separator inline size="md" class="flex-grow-1 mb-0">
                Edited {{ labels.entityNamePlural }}
            </Heading>
            <GButton size="small" outline color="blue" @click="emit('view-runtime-report')">
                Back to Runtime Report
                <FontAwesomeIcon :icon="faArrowLeft" />
            </GButton>
        </div>

        <BAlert v-if="unownedHistory" show>
            You do not own this history
            <span v-if="props.invocationId">(associated with the invocation)</span>
            so only {{ labels.entityNamePlural }} that you created against this history are shown.
        </BAlert>

        <div v-if="pages.length === 0" class="empty-state text-center p-4" data-description="page empty state">
            <p class="text-muted">{{ labels.emptyStateTitle }}</p>
            <p class="text-muted small">
                {{ labels.emptyStateDescription }}
            </p>
        </div>

        <div v-else class="page-items mt-1">
            <PageCard
                v-for="page in pages"
                :key="page.id"
                data-description="page item"
                :page="page"
                :default-title="labels.defaultTitle"
                :entity-name="labels.entityName"
                :edit-title="labels.editButton"
                :show-invocation-badge="!props.invocationId"
                :view-title="labels.viewButton"
                @edit="emit('edit', page.id, page.username)"
                @view="emit('view', page.id)" />
        </div>
    </div>
</template>

<style scoped>
.page-item:hover {
    background: var(--panel-header-bg);
}
.page-items {
    flex: 1 1 0;
    overflow-y: auto;
}
.cursor-pointer {
    cursor: pointer;
}
</style>
