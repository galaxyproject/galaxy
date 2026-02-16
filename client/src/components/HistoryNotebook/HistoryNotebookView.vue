<script setup lang="ts">
import {
    faArrowLeft,
    faComments,
    faEdit,
    faEye,
    faFileExport,
    faHistory,
    faSave,
    faSpinner,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge, BButton } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { getGalaxyInstance } from "@/app";
import type { RouterPushOptions } from "@/components/History/Content/router-push-options";
import { useConfig } from "@/composables/config";
import { useHistoryNotebookStore } from "@/stores/historyNotebookStore";
import { useHistoryStore } from "@/stores/historyStore";

import HistoryNotebookEditor from "./HistoryNotebookEditor.vue";
import HistoryNotebookList from "./HistoryNotebookList.vue";
import HistoryNotebookSplit from "./HistoryNotebookSplit.vue";
import NotebookChatPanel from "./NotebookChatPanel.vue";
import NotebookRevisionList from "./NotebookRevisionList.vue";
import NotebookRevisionView from "./NotebookRevisionView.vue";
import ClickToEdit from "@/components/ClickToEdit.vue";
import Markdown from "@/components/Markdown/Markdown.vue";

const props = defineProps<{
    historyId: string;
    notebookId?: string;
    displayOnly?: boolean;
}>();

const router = useRouter();
const store = useHistoryNotebookStore();
const historyStore = useHistoryStore();
const { config } = useConfig();

const agentsAvailable = computed(() => !!config.value?.llm_api_configured);

const _historyName = computed(() => {
    const history = historyStore.getHistoryById(props.historyId);
    return history?.name || "History";
});

const markdownConfig = computed(() => {
    if (!store.currentNotebook) {
        return null;
    }
    // In displayOnly mode use the server-resolved content (IDs encoded)
    // so the Markdown renderer can find dataset references.  In editor mode use the
    // raw editor content for editing.
    const content = props.displayOnly ? (store.currentNotebook.content ?? store.currentContent) : store.currentContent;
    return {
        id: store.currentNotebook.id,
        title: store.currentTitle || "Untitled Notebook",
        content,
        model_class: "HistoryNotebook",
        update_time: store.currentNotebook.update_time,
    };
});

onMounted(async () => {
    await store.loadNotebooks(props.historyId);
    if (props.notebookId) {
        await store.loadNotebook(props.notebookId);
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
        if (props.notebookId) {
            await store.loadNotebook(props.notebookId);
        }
    },
);

watch(
    () => props.notebookId,
    async (newId) => {
        if (newId) {
            await store.loadNotebook(newId);
        } else {
            store.clearCurrentNotebook();
        }
    },
);

function handleSelect(notebookId: string) {
    const Galaxy = getGalaxyInstance();
    const isWmActive = Galaxy?.frame?.active;

    if (isWmActive) {
        const notebook = store.notebooks.find((n) => n.id === notebookId);
        const title = notebook?.title || "Notebook";
        const url = `/histories/${props.historyId}/notebooks/${notebookId}?displayOnly=true`;
        const options: RouterPushOptions = {
            title: `Notebook: ${title}`,
            preventWindowManager: false,
        };
        // @ts-ignore - monkeypatched router, drop with migration.
        router.push(url, options);
    } else {
        router.push(`/histories/${props.historyId}/notebooks/${notebookId}`);
    }
}

async function handleCreate() {
    const notebook = await store.createNotebook({ title: "Untitled Notebook" });
    if (notebook) {
        router.push(`/histories/${props.historyId}/notebooks/${notebook.id}`);
    }
}

function handleView(notebookId: string) {
    router.push(`/histories/${props.historyId}/notebooks/${notebookId}?displayOnly=true`);
}

function handlePreview() {
    if (props.notebookId) {
        router.push(`/histories/${props.historyId}/notebooks/${props.notebookId}?displayOnly=true`);
    }
}

function handleEdit() {
    if (props.notebookId) {
        router.push(`/histories/${props.historyId}/notebooks/${props.notebookId}`);
    }
}

function handleBack() {
    store.clearCurrentNotebook();
    router.push(`/histories/${props.historyId}/notebooks`);
}

async function handleSave() {
    await store.saveNotebook();
}

function handleTitleChange(newTitle: string) {
    store.updateTitle(newTitle);
}

async function handleExportToPage() {
    if (store.isDirty) {
        await store.saveNotebook();
    }
    const notebook = store.currentNotebook;
    if (notebook) {
        router.push(`/pages/create?notebook_id=${notebook.id}&history_id=${props.historyId}`);
    }
}

function handleRevisionSelect(revisionId: string) {
    store.loadRevision(revisionId);
}

function handleRevisionRestore(revisionId: string) {
    store.restoreRevision(revisionId);
}
</script>

<template>
    <div class="history-notebook-view d-flex flex-column h-100" data-description="history notebook view">
        <BAlert v-if="store.isLoadingList" variant="info" show>
            <FontAwesomeIcon :icon="faSpinner" spin />
            Loading notebooks...
        </BAlert>

        <BAlert v-else-if="store.error" variant="danger" show dismissible @dismissed="store.error = null">
            {{ store.error }}
        </BAlert>

        <template v-else-if="!notebookId">
            <HistoryNotebookList
                :notebooks="store.notebooks"
                @select="handleSelect"
                @view="handleView"
                @create="handleCreate" />
        </template>

        <!-- Notebook loaded in displayOnly mode -- rendered view -->
        <template v-else-if="store.hasCurrentNotebook && displayOnly">
            <div
                class="notebook-display-toolbar d-flex align-items-center p-2 border-bottom"
                data-description="notebook display toolbar">
                <BButton variant="link" size="sm" data-description="notebook manage button" @click="handleBack">
                    <FontAwesomeIcon :icon="faArrowLeft" />
                    Manage History Notebooks
                </BButton>
                <span class="flex-grow-1 text-center font-weight-bold">
                    {{ store.currentTitle || "Untitled Notebook" }}
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

        <!-- Notebook loaded: viewing a specific revision -->
        <template v-else-if="store.hasCurrentNotebook && store.selectedRevision">
            <NotebookRevisionView
                :revision="store.selectedRevision"
                :is-reverting="store.isReverting"
                @back="store.clearSelectedRevision"
                @restore="handleRevisionRestore" />
        </template>

        <!-- Notebook loaded in edit mode -- toolbar + editor + optional revision panel -->
        <template v-else-if="store.hasCurrentNotebook">
            <div
                class="notebook-toolbar d-flex align-items-center p-2 border-bottom"
                data-description="notebook toolbar">
                <BButton variant="link" size="sm" data-description="notebook manage button" @click="handleBack">
                    <FontAwesomeIcon :icon="faArrowLeft" />
                    Manage History Notebooks
                </BButton>
                <ClickToEdit
                    :value="store.currentTitle || 'Untitled Notebook'"
                    tag-name="span"
                    placeholder="Untitled Notebook"
                    class="flex-grow-1 text-center font-weight-bold"
                    data-description="notebook toolbar title"
                    @input="handleTitleChange" />
                <BButton
                    variant="outline-primary"
                    size="sm"
                    class="mr-2"
                    data-description="notebook revisions button"
                    @click="store.toggleRevisions">
                    <FontAwesomeIcon :icon="faHistory" />
                    Revisions
                    <BBadge v-if="store.revisionCount > 0" variant="light" class="ml-1">
                        {{ store.revisionCount }}
                    </BBadge>
                </BButton>
                <BButton
                    variant="outline-primary"
                    size="sm"
                    class="mr-2"
                    data-description="notebook export to page button"
                    @click="handleExportToPage">
                    <FontAwesomeIcon :icon="faFileExport" />
                    Export to Page
                </BButton>
                <BButton
                    variant="outline-primary"
                    size="sm"
                    class="mr-2"
                    data-description="notebook preview button"
                    @click="handlePreview">
                    <FontAwesomeIcon :icon="faEye" />
                    Preview
                </BButton>
                <BButton
                    v-if="agentsAvailable"
                    :variant="store.showChatPanel ? 'primary' : 'outline-primary'"
                    size="sm"
                    class="mr-2"
                    data-description="notebook chat button"
                    @click="store.toggleChatPanel">
                    <FontAwesomeIcon :icon="faComments" />
                    Chat
                </BButton>
                <BButton
                    variant="primary"
                    size="sm"
                    data-description="notebook save button"
                    :disabled="!store.canSave"
                    @click="handleSave">
                    <FontAwesomeIcon :icon="store.isSaving ? faSpinner : faSave" :spin="store.isSaving" />
                    Save
                </BButton>
                <span
                    v-if="store.isDirty"
                    class="ml-2 text-warning small"
                    data-description="notebook unsaved indicator">
                    Unsaved
                </span>
            </div>

            <div class="notebook-body d-flex flex-grow-1 overflow-hidden">
                <HistoryNotebookSplit v-if="store.showChatPanel && notebookId">
                    <template v-slot:editor>
                        <HistoryNotebookEditor
                            :history-id="historyId"
                            :content="store.currentContent"
                            @update:content="store.updateContent" />
                    </template>
                    <template v-slot:chat>
                        <NotebookChatPanel
                            :history-id="historyId"
                            :notebook-id="notebookId"
                            :notebook-content="store.currentContent" />
                    </template>
                </HistoryNotebookSplit>
                <template v-else>
                    <div class="notebook-content flex-grow-1 overflow-auto">
                        <HistoryNotebookEditor
                            :history-id="historyId"
                            :content="store.currentContent"
                            @update:content="store.updateContent" />
                    </div>
                    <div v-if="store.showRevisions" class="notebook-revision-panel border-left">
                        <NotebookRevisionList
                            :revisions="store.revisions"
                            :is-loading="store.isLoadingRevisions"
                            :is-reverting="store.isReverting"
                            @select="handleRevisionSelect"
                            @restore="handleRevisionRestore" />
                    </div>
                </template>
            </div>
        </template>

        <BAlert v-else-if="store.isLoadingNotebook" variant="info" show>
            <FontAwesomeIcon :icon="faSpinner" spin />
            Loading notebook...
        </BAlert>
    </div>
</template>

<style scoped>
.history-notebook-view {
    background: var(--body-bg);
}
.notebook-toolbar,
.notebook-display-toolbar {
    background: var(--panel-header-bg);
}
.notebook-content {
    padding: 1rem;
}
.notebook-revision-panel {
    width: 300px;
    min-width: 300px;
    overflow-y: auto;
    background: var(--body-bg);
}
</style>
