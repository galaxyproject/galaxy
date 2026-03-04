<script setup lang="ts">
import {
    faArrowLeft,
    faComments,
    faEdit,
    faEye,
    faHistory,
    faSave,
    faSpinner,
    faUsers,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge, BButton } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { getGalaxyInstance } from "@/app";
import type { RouterPushOptions } from "@/components/History/Content/router-push-options";
import { PAGE_LABELS, PERMISSIONS_LABELS } from "@/components/Page/constants";
import { useConfig } from "@/composables/config";
import { useHistoryStore } from "@/stores/historyStore";
import { type PageEditorMode, usePageEditorStore } from "@/stores/pageEditorStore";

import EditorSplitView from "./EditorSplitView.vue";
import ObjectPermissionsModal from "./ObjectPermissionsModal.vue";
import PageChatPanel from "./PageChatPanel.vue";
import PageRevisionList from "./PageRevisionList.vue";
import PageRevisionView from "./PageRevisionView.vue";
import ClickToEdit from "@/components/ClickToEdit.vue";
import Markdown from "@/components/Markdown/Markdown.vue";
import MarkdownEditor from "@/components/Markdown/MarkdownEditor.vue";

const props = defineProps<{
    pageId: string;
    historyId?: string;
    displayOnly?: boolean;
}>();

const router = useRouter();
const store = usePageEditorStore();
const historyStore = useHistoryStore();
const { config } = useConfig();

const agentsAvailable = computed(() => !!config.value?.llm_api_configured);

const editorMode = computed<PageEditorMode>(() => (props.historyId ? "history" : "standalone"));
const isStandalone = computed(() => editorMode.value === "standalone");

const labels = computed(() => PAGE_LABELS[editorMode.value]);

const editorTitle = computed(() => {
    if (props.historyId) {
        const history = historyStore.getHistoryById(props.historyId);
        return history?.name || labels.value.entityName;
    }
    return store.currentTitle || labels.value.defaultTitle;
});

const markdownEditorMode = computed<"page" | "report">(() => "page");

const markdownConfig = computed(() => {
    if (!store.currentPage) {
        return null;
    }
    const content = props.displayOnly ? (store.currentPage.content ?? store.currentContent) : store.currentContent;
    return {
        id: store.currentPage.id,
        title: store.currentTitle || labels.value.defaultTitle,
        content,
        model_class: "Page",
        update_time: store.currentPage.update_time,
    };
});

const showPermissions = ref(false);

onMounted(async () => {
    store.mode = editorMode.value;
    if (props.historyId) {
        store.historyId = props.historyId;
    }
    await store.loadPage(props.pageId);
});

onUnmounted(() => {
    if (!props.displayOnly) {
        store.$reset();
    }
});

watch(
    () => props.pageId,
    async (newId) => {
        if (newId) {
            await store.loadPage(newId);
        }
    },
);

function handleBack() {
    store.clearCurrentPage();
    if (props.historyId) {
        router.push(`/histories/${props.historyId}/pages`);
    } else {
        router.push("/pages/list");
    }
}

function handlePreview() {
    if (props.historyId) {
        router.push(`/histories/${props.historyId}/pages/${props.pageId}?displayOnly=true`);
    } else {
        // Standalone: open in window manager or navigate
        const Galaxy = getGalaxyInstance();
        const isWmActive = Galaxy?.frame?.active;
        if (isWmActive) {
            const url = `/pages/editor?id=${props.pageId}&displayOnly=true`;
            const options: RouterPushOptions = {
                title: `${labels.value.entityName}: ${store.currentTitle || labels.value.defaultTitle}`,
                preventWindowManager: false,
            };
            // @ts-ignore - monkeypatched router
            router.push(url, options);
        } else {
            router.push(`/pages/editor?id=${props.pageId}&displayOnly=true`);
        }
    }
}

function handleEdit() {
    if (props.historyId) {
        router.push(`/histories/${props.historyId}/pages/${props.pageId}`);
    } else {
        router.push(`/pages/editor?id=${props.pageId}`);
    }
}

async function handleSave() {
    await store.savePage();
}

async function handleSaveAndView() {
    await store.savePage();
    if (store.currentPage) {
        const Galaxy = getGalaxyInstance();
        const isWmActive = Galaxy?.frame?.active;
        if (isWmActive) {
            const url = `/published/page?id=${props.pageId}&embed=true`;
            const options: RouterPushOptions = {
                title: `${labels.value.entityName}: ${store.currentTitle || labels.value.defaultTitle}`,
                preventWindowManager: false,
            };
            // @ts-ignore - monkeypatched router
            router.push(url, options);
        } else {
            const data = store.currentPage as any;
            if (data.username && data.slug) {
                window.location.href = `/u/${data.username}/p/${data.slug}`;
            }
        }
    }
}

function handleTitleChange(newTitle: string) {
    store.updateTitle(newTitle);
}

function handleContentUpdate(newContent: string) {
    store.updateContent(newContent);
}

function handleRevisionSelect(revisionId: string) {
    store.loadRevision(revisionId);
}

function handleRevisionRestore(revisionId: string) {
    store.restoreRevision(revisionId);
}
</script>

<template>
    <div class="page-editor-view d-flex flex-column h-100" data-description="page editor view">
        <BAlert v-if="store.isLoadingPage && !store.hasCurrentPage" variant="info" show>
            <FontAwesomeIcon :icon="faSpinner" spin />
            Loading page...
        </BAlert>

        <BAlert v-else-if="store.error" variant="danger" show dismissible @dismissed="store.error = null">
            {{ store.error }}
        </BAlert>

        <!-- Display-only mode: rendered view -->
        <template v-else-if="store.hasCurrentPage && displayOnly">
            <div
                class="page-display-toolbar d-flex align-items-center p-2 border-bottom"
                data-description="page display toolbar">
                <BButton variant="link" size="sm" data-description="page back button" @click="handleBack">
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

        <!-- Viewing a specific revision -->
        <template v-else-if="store.hasCurrentPage && store.selectedRevision">
            <PageRevisionView
                :revision="store.selectedRevision"
                :current-content="store.currentContent"
                :previous-content="store.previousRevisionContent"
                :is-newest-revision="store.isNewestRevision"
                :is-oldest-revision="store.isOldestRevision"
                :view-mode="store.revisionViewMode"
                :is-reverting="store.isReverting"
                @back="store.clearSelectedRevision"
                @restore="handleRevisionRestore"
                @update:viewMode="store.revisionViewMode = $event" />
        </template>

        <!-- Edit mode: toolbar + editor + optional chat/revision panels -->
        <template v-else-if="store.hasCurrentPage">
            <div
                class="page-toolbar d-flex align-items-center p-2 border-bottom"
                data-description="page editor toolbar">
                <BButton variant="link" size="sm" data-description="page back button" @click="handleBack">
                    <FontAwesomeIcon :icon="faArrowLeft" />
                    {{ labels.editorBackLabel }}
                </BButton>
                <ClickToEdit
                    :value="store.currentTitle || labels.defaultTitle"
                    tag-name="span"
                    :placeholder="labels.defaultTitle"
                    class="flex-grow-1 text-center font-weight-bold"
                    data-description="page editor title"
                    @input="handleTitleChange" />
                <BButton
                    variant="outline-primary"
                    size="sm"
                    class="mr-2"
                    data-description="page revisions button"
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
                    data-description="page preview button"
                    @click="handlePreview">
                    <FontAwesomeIcon :icon="faEye" />
                    Preview
                </BButton>
                <BButton
                    v-if="agentsAvailable"
                    :variant="store.showChatPanel ? 'primary' : 'outline-primary'"
                    size="sm"
                    class="mr-2"
                    data-description="page chat button"
                    @click="store.toggleChatPanel">
                    <FontAwesomeIcon :icon="faComments" />
                    Chat
                </BButton>
                <template v-if="isStandalone">
                    <ObjectPermissionsModal
                        id="object-permissions-modal"
                        v-model="showPermissions"
                        :markdown-content="store.currentContent" />
                    <BButton
                        v-b-modal:object-permissions-modal
                        variant="outline-primary"
                        size="sm"
                        class="mr-2"
                        data-description="page permissions button">
                        <FontAwesomeIcon :icon="faUsers" />
                        Permissions
                    </BButton>
                </template>
                <BButton
                    variant="primary"
                    size="sm"
                    :class="{ 'mr-2': isStandalone }"
                    data-description="page save button"
                    :disabled="!store.canSave"
                    @click="handleSave">
                    <FontAwesomeIcon :icon="store.isSaving ? faSpinner : faSave" :spin="store.isSaving" />
                    Save
                </BButton>
                <BButton
                    v-if="isStandalone"
                    variant="primary"
                    size="sm"
                    data-description="page save-view button"
                    :disabled="!store.canSave"
                    @click="handleSaveAndView">
                    <FontAwesomeIcon :icon="faEye" />
                    Save &amp; View
                </BButton>
                <span v-if="store.isDirty" class="ml-2 text-warning small" data-description="page unsaved indicator">
                    Unsaved
                </span>
            </div>

            <div class="page-body d-flex flex-grow-1 overflow-hidden">
                <EditorSplitView v-if="store.showChatPanel">
                    <template v-slot:editor>
                        <MarkdownEditor
                            :markdown-text="store.currentContent"
                            :mode="markdownEditorMode"
                            :title="editorTitle"
                            @update="handleContentUpdate" />
                    </template>
                    <template v-slot:chat>
                        <PageChatPanel :history-id="historyId" :page-id="pageId" :page-content="store.currentContent" />
                    </template>
                </EditorSplitView>
                <template v-else>
                    <div class="page-content flex-grow-1 overflow-auto">
                        <MarkdownEditor
                            :markdown-text="store.currentContent"
                            :mode="markdownEditorMode"
                            :title="editorTitle"
                            @update="handleContentUpdate" />
                    </div>
                    <div v-if="store.showRevisions" class="page-revision-panel border-left">
                        <PageRevisionList
                            :revisions="store.revisions"
                            :is-loading="store.isLoadingRevisions"
                            :is-reverting="store.isReverting"
                            @select="handleRevisionSelect"
                            @restore="handleRevisionRestore" />
                    </div>
                </template>
            </div>
        </template>
    </div>
</template>

<style scoped>
.page-editor-view {
    background: var(--body-bg);
}
.page-toolbar,
.page-display-toolbar {
    background: var(--panel-header-bg);
}
.page-content {
    padding: 1rem;
}
.page-revision-panel {
    width: 300px;
    min-width: 300px;
    overflow-y: auto;
    background: var(--body-bg);
}
</style>
