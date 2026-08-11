<script setup lang="ts">
import { faCopy, faSpinner, faUsers } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { PAGE_LABELS } from "@/components/Page/constants";
import { useConfirmDialog } from "@/composables/confirmDialog.js";
import { useSaveChangesModal } from "@/composables/useSaveChangesModal";
import { useWindowAwareNavigation } from "@/composables/windowAwareNavigation";
import { useHistoryStore } from "@/stores/historyStore";
import { type PageEditorMode, usePageEditorStore } from "@/stores/pageEditorStore";
import { useUserStore } from "@/stores/userStore.js";

import GButton from "../BaseComponents/GButton.vue";
import GModal from "../BaseComponents/GModal.vue";
import SaveChangesModal from "../Workflow/Editor/SaveChangesModal.vue";
import ObjectPermissionsModal from "./ObjectPermissionsModal.vue";
import PageDisplayOnly from "./PageDisplayOnly.vue";
import PageDisplayToolbar from "./PageDisplayToolbar.vue";
import PageRevisionList from "./PageRevisionList.vue";
import PageRevisionView from "./PageRevisionView.vue";
import MarkdownEditor from "@/components/Markdown/MarkdownEditor.vue";

const props = defineProps<{
    pageId: string;
    historyId?: string;
    invocationId?: string;
    displayOnly?: boolean;
    hideHeader?: boolean;
}>();

const { confirm } = useConfirmDialog();
const router = useRouter();
const { pushToFrameOrPage } = useWindowAwareNavigation();
const store = usePageEditorStore();
const historyStore = useHistoryStore();
const userStore = useUserStore();

const editorMode = computed<PageEditorMode>(() =>
    props.invocationId ? "invocation" : props.historyId ? "history" : "standalone",
);
const isStandalone = computed(() => editorMode.value === "standalone");

const labels = computed(() => PAGE_LABELS[editorMode.value]);

const editorTitle = computed(() => {
    if (props.historyId) {
        const history = historyStore.getHistoryById(props.historyId);
        return `History: ${history?.name}` || labels.value.entityName;
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

const isOwnedPage = computed(() => userStore.matchesCurrentUsername(store.currentPage?.username));

const showPermissions = ref(false);

const { showSaveChangesModal, pendingNavUrl, handleSaveChangesProceed } = useSaveChangesModal(
    computed(() => store.isDirty),
    () => store.savePage(),
    router,
);

onMounted(async () => {
    store.mode = editorMode.value;
    if (props.historyId) {
        store.setCurrentContext(props.historyId);
    }
    await store.loadPage(props.pageId);
    window.addEventListener("beforeunload", handleBeforeUnload);
});

onUnmounted(() => {
    window.removeEventListener("beforeunload", handleBeforeUnload);
    if (!props.displayOnly) {
        // Clear editor-scoped state but leave store.error alone so a save failure
        // remains visible across the transient unmount/remount that error-state
        // re-renders trigger in the parent.
        store.clearCurrentPage();
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
    if (props.invocationId) {
        router.push(`/workflows/invocations/${props.invocationId}/reports`);
    } else if (props.historyId) {
        router.push(`/histories/${props.historyId}/pages`);
    } else {
        router.push("/pages/list");
    }
}

/**
 * If the page is dirty, prompt the user before leaving the page via non-internal navigation
 * (e.g., closing the tab, refreshing page or navigating to a different site).
 */
function handleBeforeUnload(event: BeforeUnloadEvent) {
    if (store.isDirty) {
        event.preventDefault();
        event.returnValue = "";
    }
}

/** Open basic md display in window manager when active, else navigate inline according to context */
function handlePreview() {
    const framedUrl = `/pages/editor?id=${props.pageId}&displayOnly=true&hideHeader=true`;

    let inlineUrl: string;
    if (props.invocationId) {
        inlineUrl = `/workflows/invocations/${props.invocationId}/reports?id=${props.pageId}`;
    } else if (props.historyId) {
        inlineUrl = `/histories/${props.historyId}/pages/${props.pageId}?displayOnly=true`;
    } else {
        inlineUrl = `/pages/editor?id=${props.pageId}&displayOnly=true`;
    }

    pushToFrameOrPage({
        framedUrl,
        inlineUrl,
        title: `${labels.value.entityName}: ${store.currentTitle || labels.value.defaultTitle}`,
    });
}

async function handleEdit() {
    let editingPageId: string | undefined = props.pageId;

    if (!isOwnedPage.value) {
        const entity = labels.value.entityName;

        const confirmed = await confirm(
            `You are not the owner of this ${entity}. To edit it, a copy with its contents, owned by you, will be created. Do you want to proceed?`,
            {
                title: `Copy this ${entity}?`,
                okText: `Copy ${entity}`,
                okIcon: faCopy,
            },
        );
        if (!confirmed) {
            return;
        }

        const copiedPage = await store.createPage({
            title: store.currentTitle ? `Copy of "${store.currentTitle}"` : labels.value.defaultTitle,
            content: store.currentContent,
        });

        editingPageId = copiedPage?.id;
    }

    if (editingPageId) {
        if (props.historyId) {
            router.push(`/histories/${props.historyId}/pages/${editingPageId}`);
        } else {
            router.push(`/pages/editor?id=${editingPageId}`);
        }
    }
}

function handleContentUpdate(newContent: string) {
    store.updateContent(newContent);
}

async function handleRevisionSelect(revisionId: string) {
    await store.loadRevision(revisionId);
    store.showRevisions = false;
}

function handleRevisionRestore(revisionId: string) {
    store.restoreRevision(revisionId);
}
</script>

<template>
    <div class="page-editor-view d-flex flex-column h-100" data-description="page editor view">
        <SaveChangesModal
            :show-modal.sync="showSaveChangesModal"
            :nav-url="pendingNavUrl"
            :append-version="false"
            @on-proceed="handleSaveChangesProceed" />

        <BAlert v-if="store.error" variant="danger" show dismissible @dismissed="store.error = null">
            {{ store.error }}
        </BAlert>

        <BAlert v-if="store.isLoadingPage && !store.hasCurrentPage" variant="info" show>
            <FontAwesomeIcon :icon="faSpinner" spin />
            Loading page...
        </BAlert>

        <!-- Display-only mode: rendered view -->
        <PageDisplayOnly
            v-else-if="store.hasCurrentPage && (displayOnly || !isOwnedPage || store.currentPage?.deleted)"
            :labels="labels"
            :markdown-config="markdownConfig || undefined"
            :hide-header="props.hideHeader"
            @back="handleBack"
            @edit="handleEdit" />

        <!-- Edit mode: toolbar + editor + optional chat/revision panels -->
        <template v-else-if="store.hasCurrentPage">
            <PageDisplayToolbar :labels="labels" mode="editor" @preview="handlePreview" @back="handleBack">
                <template v-if="isStandalone" v-slot:extra-actions>
                    <ObjectPermissionsModal
                        id="object-permissions-modal"
                        v-model="showPermissions"
                        :markdown-content="store.currentContent" />
                    <GButton
                        v-b-modal:object-permissions-modal
                        color="blue"
                        outline
                        size="small"
                        data-description="page permissions button"
                        @click="showPermissions = true">
                        <FontAwesomeIcon :icon="faUsers" />
                        Permissions
                    </GButton>
                </template>
            </PageDisplayToolbar>

            <div class="page-body d-flex flex-grow-1 overflow-hidden">
                <div class="page-content flex-grow-1 overflow-auto">
                    <PageRevisionView
                        v-if="store.selectedRevision"
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
                    <MarkdownEditor
                        v-else
                        class="h-100"
                        :markdown-text="store.currentContent"
                        :mode="markdownEditorMode"
                        :title="editorTitle"
                        @update="handleContentUpdate" />
                </div>
                <GModal
                    data-description="page revisions modal"
                    fixed-height
                    :show.sync="store.showRevisions"
                    size="small"
                    :title="`${labels.entityName} Revisions`">
                    <template v-slot:header>
                        <div class="d-flex align-items-center flex-gapx-1">
                            <FontAwesomeIcon v-if="store.isLoadingRevision" :icon="faSpinner" spin fixed-width />
                            Click to select and view a revision in the editor
                        </div>
                    </template>
                    <PageRevisionList
                        :revisions="store.revisions"
                        :is-loading="store.isLoadingRevisions"
                        :is-reverting="store.isReverting"
                        :selected-revision-id="store.selectedRevision?.id"
                        @select="handleRevisionSelect"
                        @restore="handleRevisionRestore" />
                </GModal>
            </div>
        </template>
    </div>
</template>

<style scoped>
.page-editor-view {
    background: var(--body-bg);
}
.page-editor-pane {
    padding: 1rem;
    display: flex;
    flex-direction: column;
    min-height: 0;
    height: 100%;
}
</style>
