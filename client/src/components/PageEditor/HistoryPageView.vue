<script setup lang="ts">
import { faCopy, faPlus, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { PAGE_LABELS } from "@/components/Page/constants";
import { useConfirmDialog } from "@/composables/confirmDialog.js";
import { useToast } from "@/composables/toast";
import { useWindowAwareNavigation } from "@/composables/windowAwareNavigation";
import { usePageEditorStore } from "@/stores/pageEditorStore";
import { useUserStore } from "@/stores/userStore.js";
import { errorMessageAsString } from "@/utils/simple-error.js";

import HistoryPageList from "./HistoryPageList.vue";
import PageDisplayOnly from "./PageDisplayOnly.vue";
import PageEditorView from "./PageEditorView.vue";

const props = defineProps<{
    historyId: string;
    invocationId?: string;
    pageId?: string;
    displayOnly?: boolean;
}>();

const Toast = useToast();

const { confirm } = useConfirmDialog();
const router = useRouter();
const { pushToFrameOrPage } = useWindowAwareNavigation();
const userStore = useUserStore();
const store = usePageEditorStore();
const labels = computed(() => (props.invocationId ? PAGE_LABELS.invocation : PAGE_LABELS.history));

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

onMounted(async () => {
    await store.loadPages(props.historyId, props.invocationId);
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
    () => [props.historyId, props.invocationId],
    async ([newHistoryId, newInvocationId]) => {
        if (newHistoryId) {
            await store.loadPages(newHistoryId, newInvocationId);
            if (props.pageId && props.displayOnly) {
                await store.loadPageById(props.pageId);
            }
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

async function createAPage(isCopy = false) {
    const entity = labels.value.entityName;

    const modalText = isCopy
        ? `You are not the owner of this ${entity}. To edit it, a copy with its contents, owned by you, will be created. Do you want to proceed?`
        : `A new ${entity} will be created and will be added to the list of ${labels.value.entityNamePlural} for this ${props.invocationId ? "invocation" : "history"}. Do you want to proceed?`;

    const modalTitle = isCopy ? `Copy this ${entity}?` : `Create new ${entity}?`;
    const okText = isCopy ? `Copy ${entity}` : `Create ${entity}`;
    const okIcon = isCopy ? faCopy : faPlus;

    const confirmed = await confirm(modalText, {
        title: modalTitle,
        okText,
        okIcon,
    });
    if (!confirmed) {
        return;
    }

    const newPage = await store.createPage({
        title: isCopy
            ? store.currentTitle
                ? `Copy of "${store.currentTitle}"`
                : labels.value.defaultTitle
            : undefined,
        content: isCopy ? store.currentContent : undefined,
    });

    return newPage;
}

function handleView(viewingPageId: string) {
    const page = store.pages.find((n) => n.id === viewingPageId);
    const pageTitle = page?.title || labels.value.entityName;
    const inlineUrl = props.invocationId
        ? `/workflows/invocations/${props.invocationId}/reports?id=${viewingPageId}`
        : `/histories/${props.historyId}/pages/${viewingPageId}?displayOnly=true`;

    pushToFrameOrPage({
        framedUrl: `/pages/editor?id=${viewingPageId}&displayOnly=true&hideHeader=true`,
        inlineUrl,
        title: `${labels.value.entityName}: ${pageTitle}`,
    });
}

async function handleCreate() {
    try {
        const createdPage = await createAPage();
        if (createdPage) {
            handleEdit(createdPage.id, createdPage.username);
        }
    } catch (error) {
        Toast.error(errorMessageAsString(error), `Failed to create ${labels.value.entityName.toLowerCase()}`);
    }
}

async function handleEdit(editingPageId: string, ownerUsername: string) {
    let routedId: string | undefined = editingPageId;

    if (routedId && ownerUsername && !userStore.matchesCurrentUsername(ownerUsername)) {
        const copiedPage = await createAPage(true);
        routedId = copiedPage?.id;
    }

    if (routedId) {
        let editUrl = `/histories/${props.historyId}/pages/${routedId}`;
        if (props.invocationId) {
            editUrl += `?invocation_id=${props.invocationId}`;
        }
        router.push(editUrl);
    }
}

function handleBack() {
    store.clearCurrentPage();
    if (props.invocationId) {
        router.push(`/workflows/invocations/${props.invocationId}/reports`);
        return;
    }
    router.push(`/histories/${props.historyId}/pages`);
}
</script>

<template>
    <div class="history-page-view d-flex flex-column h-100" data-description="history page view">
        <!--
          Error alert is owned by PageEditorView while it is mounted (edit mode).
          Render it here only for list view and display-only mode, otherwise the
          same store.error renders twice.
        -->
        <BAlert
            v-if="store.error && (!pageId || displayOnly)"
            variant="danger"
            show
            dismissible
            @dismissed="store.error = null">
            {{ store.error }}
        </BAlert>

        <BAlert v-if="store.isLoadingList" variant="info" show>
            <FontAwesomeIcon :icon="faSpinner" spin />
            Loading {{ labels.entityNamePlural.toLowerCase() }}...
        </BAlert>

        <template v-else-if="!pageId">
            <HistoryPageList
                :history-id="props.historyId"
                :invocation-id="props.invocationId"
                :pages="store.pages"
                @view-runtime-report="router.push(`/workflows/invocations/${props.invocationId}/report`)"
                @edit="handleEdit"
                @view="handleView"
                @create="handleCreate" />
        </template>

        <!-- Display-only mode: rendered view -->
        <PageDisplayOnly
            v-else-if="store.currentPage?.id && store.currentPage.id === props.pageId && displayOnly"
            :labels="labels"
            :markdown-config="markdownConfig || undefined"
            @back="handleBack"
            @edit="handleEdit(store.currentPage.id, store.currentPage.username)" />

        <!-- Edit mode: delegate to unified PageEditorView -->
        <template v-else-if="pageId && !displayOnly">
            <PageEditorView :page-id="pageId" :history-id="historyId" :invocation-id="invocationId" />
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
</style>
