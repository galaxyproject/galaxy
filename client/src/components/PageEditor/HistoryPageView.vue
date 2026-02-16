<script setup lang="ts">
import { faArrowLeft, faEdit, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { getGalaxyInstance } from "@/app";
import type { RouterPushOptions } from "@/components/History/Content/router-push-options";
import { PAGE_LABELS } from "@/components/Page/constants";
import { usePageEditorStore } from "@/stores/pageEditorStore";

import HistoryPageList from "./HistoryPageList.vue";
import PageEditorView from "./PageEditorView.vue";
import Markdown from "@/components/Markdown/Markdown.vue";

const props = defineProps<{
    historyId: string;
    pageId?: string;
    displayOnly?: boolean;
}>();

const router = useRouter();
const store = usePageEditorStore();
const labels = PAGE_LABELS.history;

const markdownConfig = computed(() => {
    if (!store.currentPage) {
        return null;
    }
    const content = props.displayOnly ? (store.currentPage.content ?? store.currentContent) : store.currentContent;
    return {
        id: store.currentPage.id,
        title: store.currentTitle || labels.defaultTitle,
        content,
        model_class: "Page",
        update_time: store.currentPage.update_time,
    };
});

onMounted(async () => {
    await store.loadPages(props.historyId);
    if (props.pageId && props.displayOnly) {
        await store.loadPageById(props.pageId);
    }
});

onUnmounted(() => {
    if (!props.displayOnly) {
        store.$reset();
    }
});

watch(
    () => props.historyId,
    async (newId) => {
        await store.loadPages(newId);
        if (props.pageId && props.displayOnly) {
            await store.loadPageById(props.pageId);
        }
    },
);

watch(
    () => props.pageId,
    async (newId) => {
        if (newId && props.displayOnly) {
            await store.loadPageById(newId);
        } else if (!newId) {
            store.clearCurrentPage();
        }
    },
);

function handleSelect(pageId: string) {
    const Galaxy = getGalaxyInstance();
    const isWmActive = Galaxy?.frame?.active;

    if (isWmActive) {
        const page = store.pages.find((n) => n.id === pageId);
        const title = page?.title || labels.entityName;
        const url = `/histories/${props.historyId}/pages/${pageId}?displayOnly=true`;
        const options: RouterPushOptions = {
            title: `${labels.entityName}: ${title}`,
            preventWindowManager: false,
        };
        // @ts-ignore - monkeypatched router, drop with migration.
        router.push(url, options);
    } else {
        router.push(`/histories/${props.historyId}/pages/${pageId}`);
    }
}

async function handleCreate() {
    const page = await store.createPage({ title: labels.defaultTitle });
    if (page) {
        router.push(`/histories/${props.historyId}/pages/${page.id}`);
    }
}

function handleView(pageId: string) {
    router.push(`/histories/${props.historyId}/pages/${pageId}?displayOnly=true`);
}

function handleEdit() {
    if (props.pageId) {
        router.push(`/histories/${props.historyId}/pages/${props.pageId}`);
    }
}

function handleBack() {
    store.clearCurrentPage();
    router.push(`/histories/${props.historyId}/pages`);
}
</script>

<template>
    <div class="history-page-view d-flex flex-column h-100" data-description="history page view">
        <BAlert v-if="store.isLoadingList" variant="info" show>
            <FontAwesomeIcon :icon="faSpinner" spin />
            Loading {{ labels.entityNamePlural.toLowerCase() }}...
        </BAlert>

        <BAlert v-else-if="store.error" variant="danger" show dismissible @dismissed="store.error = null">
            {{ store.error }}
        </BAlert>

        <template v-else-if="!pageId">
            <HistoryPageList :pages="store.pages" @select="handleSelect" @view="handleView" @create="handleCreate" />
        </template>

        <!-- Display-only mode: rendered view -->
        <template v-else-if="store.hasCurrentPage && displayOnly">
            <div
                class="page-display-toolbar d-flex align-items-center p-2 border-bottom"
                data-description="page display toolbar">
                <BButton variant="link" size="sm" data-description="page manage button" @click="handleBack">
                    <FontAwesomeIcon :icon="faArrowLeft" />
                    {{ labels.editorBackLabel }}
                </BButton>
                <span class="flex-grow-1 text-center font-weight-bold">
                    {{ store.currentTitle || labels.defaultTitle }}
                </span>
                <BButton variant="outline-primary" size="sm" data-description="page edit button" @click="handleEdit">
                    <FontAwesomeIcon :icon="faEdit" />
                    Edit
                </BButton>
            </div>
            <div class="page-display-content overflow-auto flex-grow-1" data-description="page rendered view">
                <Markdown
                    v-if="markdownConfig"
                    :markdown-config="markdownConfig"
                    :read-only="true"
                    download-endpoint="" />
            </div>
        </template>

        <!-- Edit mode: delegate to unified PageEditorView -->
        <template v-else-if="pageId && !displayOnly">
            <PageEditorView :page-id="pageId" :history-id="historyId" />
        </template>

        <BAlert v-else-if="store.isLoadingPage" variant="info" show>
            <FontAwesomeIcon :icon="faSpinner" spin />
            Loading {{ labels.entityName.toLowerCase() }}...
        </BAlert>
    </div>
</template>

<style scoped>
.history-page-view {
    background: var(--body-bg);
}
.page-display-toolbar {
    background: var(--panel-header-bg);
}
</style>
