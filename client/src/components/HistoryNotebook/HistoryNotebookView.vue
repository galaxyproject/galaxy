<script setup lang="ts">
import { faArrowLeft, faEdit, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { getGalaxyInstance } from "@/app";
import type { RouterPushOptions } from "@/components/History/Content/router-push-options";
import { usePageEditorStore } from "@/stores/pageEditorStore";

import HistoryNotebookList from "./HistoryNotebookList.vue";
import Markdown from "@/components/Markdown/Markdown.vue";
import PageEditorView from "@/components/PageEditor/PageEditorView.vue";

const props = defineProps<{
    historyId: string;
    pageId?: string;
    displayOnly?: boolean;
}>();

const router = useRouter();
const store = usePageEditorStore();

const markdownConfig = computed(() => {
    if (!store.currentNotebook) {
        return null;
    }
    const content = props.displayOnly ? (store.currentNotebook.content ?? store.currentContent) : store.currentContent;
    return {
        id: store.currentNotebook.id,
        title: store.currentTitle || "Untitled Page",
        content,
        model_class: "Page",
        update_time: store.currentNotebook.update_time,
    };
});

onMounted(async () => {
    await store.loadNotebooks(props.historyId);
    if (props.pageId && props.displayOnly) {
        await store.loadNotebook(props.pageId);
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
        await store.loadNotebooks(newId);
        if (props.pageId && props.displayOnly) {
            await store.loadNotebook(props.pageId);
        }
    },
);

watch(
    () => props.pageId,
    async (newId) => {
        if (newId && props.displayOnly) {
            await store.loadNotebook(newId);
        } else if (!newId) {
            store.clearCurrentNotebook();
        }
    },
);

function handleSelect(pageId: string) {
    const Galaxy = getGalaxyInstance();
    const isWmActive = Galaxy?.frame?.active;

    if (isWmActive) {
        const page = store.notebooks.find((n) => n.id === pageId);
        const title = page?.title || "Page";
        const url = `/histories/${props.historyId}/pages/${pageId}?displayOnly=true`;
        const options: RouterPushOptions = {
            title: `Page: ${title}`,
            preventWindowManager: false,
        };
        // @ts-ignore - monkeypatched router, drop with migration.
        router.push(url, options);
    } else {
        router.push(`/histories/${props.historyId}/pages/${pageId}`);
    }
}

async function handleCreate() {
    const page = await store.createNotebook({ title: "Untitled Page" });
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
    store.clearCurrentNotebook();
    router.push(`/histories/${props.historyId}/pages`);
}
</script>

<template>
    <div class="history-notebook-view d-flex flex-column h-100" data-description="history notebook view">
        <BAlert v-if="store.isLoadingList" variant="info" show>
            <FontAwesomeIcon :icon="faSpinner" spin />
            Loading pages...
        </BAlert>

        <BAlert v-else-if="store.error" variant="danger" show dismissible @dismissed="store.error = null">
            {{ store.error }}
        </BAlert>

        <template v-else-if="!pageId">
            <HistoryNotebookList
                :notebooks="store.notebooks"
                @select="handleSelect"
                @view="handleView"
                @create="handleCreate" />
        </template>

        <!-- Display-only mode: rendered view -->
        <template v-else-if="store.hasCurrentNotebook && displayOnly">
            <div
                class="notebook-display-toolbar d-flex align-items-center p-2 border-bottom"
                data-description="notebook display toolbar">
                <BButton variant="link" size="sm" data-description="notebook manage button" @click="handleBack">
                    <FontAwesomeIcon :icon="faArrowLeft" />
                    Manage History Pages
                </BButton>
                <span class="flex-grow-1 text-center font-weight-bold">
                    {{ store.currentTitle || "Untitled Page" }}
                </span>
                <BButton
                    variant="outline-primary"
                    size="sm"
                    data-description="notebook edit button"
                    @click="handleEdit">
                    <FontAwesomeIcon :icon="faEdit" />
                    Edit
                </BButton>
            </div>
            <div class="notebook-display-content overflow-auto flex-grow-1" data-description="notebook rendered view">
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

        <BAlert v-else-if="store.isLoadingNotebook" variant="info" show>
            <FontAwesomeIcon :icon="faSpinner" spin />
            Loading page...
        </BAlert>
    </div>
</template>

<style scoped>
.history-notebook-view {
    background: var(--body-bg);
}
.notebook-display-toolbar {
    background: var(--panel-header-bg);
}
</style>
