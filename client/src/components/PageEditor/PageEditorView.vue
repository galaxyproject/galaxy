<script setup lang="ts">
import { faCopy, faSitemap, faSpinner, faUsers } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { PAGE_LABELS } from "@/components/Page/constants";
import { useConfirmDialog } from "@/composables/confirmDialog.js";
import { pushIgnoringNavCancel, useWindowAwareNavigation } from "@/composables/windowAwareNavigation";
import { useHistoryStore } from "@/stores/historyStore";
import { type PageEditorMode, usePageEditorStore } from "@/stores/pageEditorStore";
import { useUserStore } from "@/stores/userStore.js";

import GButton from "../BaseComponents/GButton.vue";
import GModal from "../BaseComponents/GModal.vue";
import SaveChangesModal from "../Common/SaveChangesModal.vue";
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

const saveChangesModal = ref<{ guardNavigation: (navigate: () => void) => void } | null>(null);

onMounted(async () => {
    store.mode = editorMode.value;
    if (props.historyId) {
        store.setCurrentContext(props.historyId);
    }
    await store.loadPage(props.pageId);
});

onUnmounted(() => {
    store.clearCurrentPage();
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
        pushIgnoringNavCancel(router, `/workflows/invocations/${props.invocationId}/reports`);
    } else if (props.historyId) {
        pushIgnoringNavCancel(router, `/histories/${props.historyId}/pages`);
    } else {
        pushIgnoringNavCancel(router, "/pages/list");
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

    const title = `${labels.value.entityName}: ${store.currentTitle || labels.value.defaultTitle}`;
    // With the window manager active this opens a frame rather than navigating, so the
    // router guards never see it -- ask the modal directly.
    saveChangesModal.value?.guardNavigation(() => pushToFrameOrPage({ framedUrl, inlineUrl, title }));
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
            pushIgnoringNavCancel(router, `/histories/${props.historyId}/pages/${editingPageId}`);
        } else {
            pushIgnoringNavCancel(router, `/pages/editor?id=${editingPageId}`);
        }
    }
}

async function handleExtractWorkflow() {
    if (!props.historyId || !store.currentPage) {
        return;
    }
    // The summary scans the last saved revision, so flush any edits first.
    if (store.isDirty) {
        await store.savePage();
        if (store.error) {
            return;
        }
    }
    router.push(`/histories/${props.historyId}/extract_workflow?from_page=${props.pageId}`);
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
            ref="saveChangesModal"
            :has-changes="store.isDirty"
            :on-save="() => store.savePage()"
            :on-discard="() => store.discardChanges()" />

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
                <template v-slot:extra-actions>
                    <template v-if="isStandalone">
                        <ObjectPermissionsModal :show.sync="showPermissions" :markdown-content="store.currentContent" />
                        <GButton
                            color="blue"
                            outline
                            size="small"
                            data-description="page permissions button"
                            @click="showPermissions = true">
                            <FontAwesomeIcon :icon="faUsers" />
                            Permissions
                        </GButton>
                    </template>
                    <GButton
                        v-if="props.historyId"
                        color="blue"
                        outline
                        size="small"
                        data-description="page extract workflow button"
                        @click="handleExtractWorkflow">
                        <FontAwesomeIcon :icon="faSitemap" />
                        Extract Workflow
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
