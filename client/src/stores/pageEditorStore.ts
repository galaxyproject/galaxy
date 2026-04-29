import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { type components, GalaxyApi } from "@/api";
import {
    createHistoryPage,
    type CreateHistoryPagePayload,
    deleteHistoryPage,
    fetchHistoryPage,
    fetchHistoryPages,
    fetchPageRevision,
    fetchPageRevisions,
    type HistoryPageDetails,
    type HistoryPageSummary,
    type PageRevisionDetails,
    type PageRevisionSummary,
    revertPageRevision,
    updateHistoryPage,
    type UpdateHistoryPagePayload,
} from "@/api/pages";
import { ERROR_MESSAGES } from "@/components/Page/constants";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { errorMessageAsString } from "@/utils/simple-error";

type ChatHistoryItem = components["schemas"]["ChatHistoryItemResponse"];

export type PageEditorMode = "history" | "standalone";

export const usePageEditorStore = defineStore("pageEditor", () => {
    const mode = ref<PageEditorMode>("history");
    const pages = ref<HistoryPageSummary[]>([]);
    const currentPage = ref<HistoryPageDetails | null>(null);
    const originalContent = ref("");
    const currentContent = ref("");
    const originalTitle = ref("");
    const currentTitle = ref("");
    const isLoadingList = ref(false);
    const isLoadingPage = ref(false);
    const isSaving = ref(false);
    const error = ref<string | null>(null);
    const chatError = ref<string | null>(null);
    const historyId = ref<string | null>(null);

    // Per-history "current page" ID persisted across sessions
    const currentPageIds = useUserLocalStorage<Record<string, string>>("history-page-current", {});

    // Per-page chat exchange ID persisted across panel close/reopen
    const currentChatExchangeIds = useUserLocalStorage<Record<string, string | null>>("history-page-chat-exchange", {});

    // Per-page dismissed proposal message IDs
    const dismissedChatProposals = useUserLocalStorage<Record<string, string[]>>(
        "history-page-dismissed-proposals",
        {},
    );

    // Revision state
    const revisions = ref<PageRevisionSummary[]>([]);
    const selectedRevision = ref<PageRevisionDetails | null>(null);
    const isLoadingRevisions = ref(false);
    const isLoadingRevision = ref(false);
    const isReverting = ref(false);
    const previousRevisionContent = ref<string | null>(null);
    const revisionViewMode = ref<"preview" | "changes_current" | "changes_previous">("preview");
    const showRevisions = ref(false);
    const showChatPanel = ref(false);

    // Chat history sidebar state
    const pageChatHistory = ref<ChatHistoryItem[]>([]);
    const isLoadingChatHistory = ref(false);
    const showChatHistory = ref(false);
    const chatHistoryError = ref<string | null>(null);

    const hasPages = computed(() => pages.value.length > 0);
    const hasCurrentPage = computed(() => currentPage.value !== null);
    const isDirty = computed(
        () => currentContent.value !== originalContent.value || currentTitle.value !== originalTitle.value,
    );
    const canSave = computed(() => isDirty.value && !isSaving.value);
    const revisionCount = computed(() => revisions.value.length);
    const hasRevisions = computed(() => revisions.value.length > 1);
    const isNewestRevision = computed(
        () => selectedRevision.value !== null && selectedRevision.value.id === revisions.value[0]?.id,
    );
    const isOldestRevision = computed(
        () =>
            selectedRevision.value !== null &&
            selectedRevision.value.id === revisions.value[revisions.value.length - 1]?.id,
    );

    async function loadPages(newHistoryId: string) {
        historyId.value = newHistoryId;
        isLoadingList.value = true;
        error.value = null;
        try {
            pages.value = await fetchHistoryPages(newHistoryId);
        } catch (e: unknown) {
            error.value = errorMessageAsString(e) || ERROR_MESSAGES.loadList;
        } finally {
            isLoadingList.value = false;
        }
    }

    async function loadPageById(pageId: string) {
        if (mode.value === "history" && !historyId.value) {
            return;
        }
        isLoadingPage.value = true;
        error.value = null;
        try {
            const data = await fetchHistoryPage(pageId);
            currentPage.value = data;
            // Use content_editor (raw) for the editor, not content (expanded for rendering)
            const editorContent = data.content_editor ?? data.content ?? "";
            originalContent.value = editorContent;
            currentContent.value = editorContent;
            originalTitle.value = data.title || "";
            currentTitle.value = data.title || "";
            if (historyId.value) {
                setCurrentPageId(historyId.value, pageId);
            }
        } catch (e: unknown) {
            error.value = errorMessageAsString(e) || ERROR_MESSAGES.loadPage;
        } finally {
            isLoadingPage.value = false;
        }
    }

    /** Load any page by ID — works in both history and standalone modes. */
    async function loadPage(pageId: string) {
        return loadPageById(pageId);
    }

    async function createPage(payload?: Partial<CreateHistoryPagePayload>): Promise<HistoryPageDetails | null> {
        if (!historyId.value) {
            return null;
        }
        isLoadingPage.value = true;
        error.value = null;
        try {
            const data = await createHistoryPage({
                title: payload?.title || "",
                history_id: historyId.value,
                content: payload?.content ?? null,
                content_format: "markdown",
            });
            currentPage.value = data;
            const editorContent = data.content_editor ?? data.content ?? "";
            originalContent.value = editorContent;
            currentContent.value = editorContent;
            originalTitle.value = data.title || "";
            currentTitle.value = data.title || "";
            await loadPages(historyId.value);
            return data;
        } catch (e: unknown) {
            error.value = errorMessageAsString(e) || ERROR_MESSAGES.createPage;
            throw e;
        } finally {
            isLoadingPage.value = false;
        }
    }

    async function savePage(editSource?: string) {
        if (!currentPage.value || !isDirty.value) {
            return;
        }
        // In standalone mode, default edit_source to "user"
        if (mode.value === "standalone" && editSource === undefined) {
            editSource = "user";
        }
        isSaving.value = true;
        error.value = null;
        try {
            const payload: UpdateHistoryPagePayload = {
                content: currentContent.value,
                content_format: "markdown",
                title: currentTitle.value || undefined,
                edit_source: editSource,
            };
            const data = await updateHistoryPage(currentPage.value.id, payload);
            currentPage.value = data;
            // Use current values (what the user typed) as the baseline, not data values
            // which may be transformed by rewrite_content_for_export for rendering.
            originalContent.value = currentContent.value;
            originalTitle.value = currentTitle.value;
            // Sync the pages list so handleSelect reads the updated title
            const idx = pages.value.findIndex((n) => n.id === data.id);
            if (idx !== -1) {
                pages.value[idx] = {
                    ...pages.value[idx]!,
                    title: currentTitle.value,
                    update_time: data.update_time,
                };
            }
        } catch (e: unknown) {
            error.value = errorMessageAsString(e) || ERROR_MESSAGES.savePage;
            throw e;
        } finally {
            isSaving.value = false;
        }
    }

    async function deleteCurrentPage() {
        if (!historyId.value || !currentPage.value) {
            return;
        }
        try {
            const deletedId = currentPage.value.id;
            await deleteHistoryPage(deletedId);
            clearCurrentPageId(historyId.value);
            clearCurrentChatExchangeId(deletedId);
            clearDismissedProposals(deletedId);
            currentPage.value = null;
            originalContent.value = "";
            currentContent.value = "";
            originalTitle.value = "";
            currentTitle.value = "";
            await loadPages(historyId.value);
        } catch (e: unknown) {
            error.value = errorMessageAsString(e) || ERROR_MESSAGES.deletePage;
            throw e;
        }
    }

    function updateContent(content: string) {
        currentContent.value = content;
    }

    function updateTitle(title: string) {
        currentTitle.value = title;
    }

    function discardChanges() {
        currentContent.value = originalContent.value;
        currentTitle.value = originalTitle.value;
    }

    function clearCurrentPage() {
        currentPage.value = null;
        originalContent.value = "";
        currentContent.value = "";
        originalTitle.value = "";
        currentTitle.value = "";
        showChatPanel.value = false;
        chatError.value = null;
        pageChatHistory.value = [];
        showChatHistory.value = false;
        chatHistoryError.value = null;
        clearRevisionState();
    }

    // --- Current page resolution ---

    function getCurrentPageId(forHistoryId: string): string | null {
        return currentPageIds.value[forHistoryId] || null;
    }

    function setCurrentPageId(forHistoryId: string, pageId: string) {
        currentPageIds.value = { ...currentPageIds.value, [forHistoryId]: pageId };
    }

    function clearCurrentPageId(forHistoryId: string) {
        const { [forHistoryId]: _removed, ...rest } = currentPageIds.value;
        currentPageIds.value = rest;
    }

    // --- Chat exchange persistence ---

    function getCurrentChatExchangeId(pageId: string): string | null {
        return currentChatExchangeIds.value[pageId] ?? null;
    }

    function setCurrentChatExchangeId(pageId: string, exchangeId: string | null) {
        currentChatExchangeIds.value = { ...currentChatExchangeIds.value, [pageId]: exchangeId };
    }

    function clearCurrentChatExchangeId(pageId: string) {
        const { [pageId]: _removed, ...rest } = currentChatExchangeIds.value;
        currentChatExchangeIds.value = rest;
    }

    // --- Dismissed proposals persistence ---

    function getDismissedProposals(pageId: string): string[] {
        return dismissedChatProposals.value[pageId] ?? [];
    }

    function addDismissedProposal(pageId: string, messageId: string) {
        const current = dismissedChatProposals.value[pageId] ?? [];
        if (!current.includes(messageId)) {
            dismissedChatProposals.value = {
                ...dismissedChatProposals.value,
                [pageId]: [...current, messageId],
            };
        }
    }

    function clearDismissedProposals(pageId: string) {
        const { [pageId]: _removed, ...rest } = dismissedChatProposals.value;
        dismissedChatProposals.value = rest;
    }

    // --- Chat history actions ---

    async function loadPageChatHistory(pageId: string) {
        isLoadingChatHistory.value = true;
        chatHistoryError.value = null;
        try {
            const { data, error } = await GalaxyApi().GET("/api/chat/page/{page_id}/history", {
                params: { path: { page_id: pageId }, query: { limit: 50 } },
            });
            if (error) {
                chatHistoryError.value = errorMessageAsString(error);
            } else {
                pageChatHistory.value = data ?? [];
            }
        } catch (e) {
            chatHistoryError.value = errorMessageAsString(e);
        } finally {
            isLoadingChatHistory.value = false;
        }
    }

    async function deletePageChatExchanges(pageId: string, ids: string[]) {
        const { error } = await GalaxyApi().PUT("/api/chat/exchanges/batch/delete", {
            body: { ids },
        });
        if (error) {
            throw Error(errorMessageAsString(error));
        }
        pageChatHistory.value = pageChatHistory.value.filter((item) => !ids.includes(item.id));
        const activeId = currentChatExchangeIds.value[pageId];
        if (activeId && ids.includes(activeId)) {
            setCurrentChatExchangeId(pageId, null);
        }
    }

    function toggleChatHistory() {
        showChatHistory.value = !showChatHistory.value;
    }

    async function resolveCurrentPage(forHistoryId: string): Promise<string> {
        // Always populate the list so callers can look up titles
        await loadPages(forHistoryId);

        const storedId = getCurrentPageId(forHistoryId);
        if (storedId) {
            const exists = pages.value.some((n) => n.id === storedId);
            if (exists) {
                return storedId;
            }
            // stale mapping — clear and re-resolve below
            clearCurrentPageId(forHistoryId);
        }

        if (pages.value.length > 0) {
            const sorted = [...pages.value].sort(
                (a, b) => new Date(b.update_time).getTime() - new Date(a.update_time).getTime(),
            );
            const id = sorted[0]!.id;
            setCurrentPageId(forHistoryId, id);
            return id;
        }

        // No pages exist — create one
        const created = await createHistoryPage({
            title: "",
            history_id: forHistoryId,
            content: null,
            content_format: "markdown",
        });
        setCurrentPageId(forHistoryId, created.id);
        return created.id;
    }

    // --- Revision actions ---

    async function loadRevisions() {
        if (!currentPage.value) {
            return;
        }
        isLoadingRevisions.value = true;
        try {
            revisions.value = await fetchPageRevisions(currentPage.value.id, { sortDesc: true });
        } catch (e: unknown) {
            error.value = errorMessageAsString(e) || ERROR_MESSAGES.loadRevisions;
        } finally {
            isLoadingRevisions.value = false;
        }
    }

    async function loadRevision(revisionId: string) {
        if (!currentPage.value) {
            return;
        }
        isLoadingRevision.value = true;
        try {
            selectedRevision.value = await fetchPageRevision(currentPage.value.id, revisionId);
            // Fetch predecessor revision content
            const idx = revisions.value.findIndex((r) => r.id === revisionId);
            if (idx >= 0 && idx + 1 < revisions.value.length) {
                const predecessorId = revisions.value[idx + 1]!.id;
                const predecessor = await fetchPageRevision(currentPage.value.id, predecessorId);
                previousRevisionContent.value = predecessor.content || "";
            } else {
                previousRevisionContent.value = null;
            }
        } catch (e: unknown) {
            error.value = errorMessageAsString(e) || ERROR_MESSAGES.loadRevision;
        } finally {
            isLoadingRevision.value = false;
        }
    }

    async function restoreRevision(revisionId: string) {
        if (!currentPage.value) {
            return;
        }
        isReverting.value = true;
        try {
            await revertPageRevision(currentPage.value.id, revisionId);
            // Revert returns the new revision; reload the full page to get updated details
            await loadPageById(currentPage.value.id);
            selectedRevision.value = null;
            showRevisions.value = false;
            await loadRevisions();
        } catch (e: unknown) {
            error.value = errorMessageAsString(e) || ERROR_MESSAGES.restoreRevision;
        } finally {
            isReverting.value = false;
        }
    }

    function toggleRevisions() {
        showRevisions.value = !showRevisions.value;
        if (showRevisions.value) {
            showChatPanel.value = false;
            loadRevisions();
        } else {
            selectedRevision.value = null;
        }
    }

    function toggleChatPanel() {
        showChatPanel.value = !showChatPanel.value;
        if (showChatPanel.value && showRevisions.value) {
            showRevisions.value = false;
            selectedRevision.value = null;
        }
    }

    function clearSelectedRevision() {
        selectedRevision.value = null;
        previousRevisionContent.value = null;
        revisionViewMode.value = "preview";
    }

    function clearRevisionState() {
        revisions.value = [];
        selectedRevision.value = null;
        previousRevisionContent.value = null;
        isLoadingRevisions.value = false;
        isLoadingRevision.value = false;
        isReverting.value = false;
        showRevisions.value = false;
        revisionViewMode.value = "preview";
    }

    /** Reset ephemeral state. Does NOT clear currentPageIds (persisted cross-session). */
    function $reset() {
        mode.value = "history";
        pages.value = [];
        currentPage.value = null;
        originalContent.value = "";
        currentContent.value = "";
        originalTitle.value = "";
        currentTitle.value = "";
        isLoadingList.value = false;
        isLoadingPage.value = false;
        isSaving.value = false;
        error.value = null;
        chatError.value = null;
        historyId.value = null;
        showChatPanel.value = false;
        pageChatHistory.value = [];
        isLoadingChatHistory.value = false;
        showChatHistory.value = false;
        chatHistoryError.value = null;
        clearRevisionState();
    }

    return {
        mode,
        pages,
        currentPage,
        currentContent,
        currentTitle,
        isLoadingList,
        isLoadingPage,
        isSaving,
        error,
        chatError,
        historyId,
        hasPages,
        hasCurrentPage,
        isDirty,
        canSave,
        loadPages,
        loadPageById,
        loadPage,
        createPage,
        savePage,
        deleteCurrentPage,
        updateContent,
        updateTitle,
        discardChanges,
        clearCurrentPage,
        // Current page resolution
        currentPageIds,
        getCurrentPageId,
        setCurrentPageId,
        clearCurrentPageId,
        resolveCurrentPage,
        // Chat exchange persistence
        currentChatExchangeIds,
        getCurrentChatExchangeId,
        setCurrentChatExchangeId,
        clearCurrentChatExchangeId,
        // Dismissed proposals persistence
        getDismissedProposals,
        addDismissedProposal,
        clearDismissedProposals,
        // Chat history state
        pageChatHistory,
        isLoadingChatHistory,
        showChatHistory,
        chatHistoryError,
        loadPageChatHistory,
        deletePageChatExchanges,
        toggleChatHistory,
        // Revision state
        revisionViewMode,
        revisions,
        selectedRevision,
        previousRevisionContent,
        isNewestRevision,
        isOldestRevision,
        isLoadingRevisions,
        isLoadingRevision,
        isReverting,
        showRevisions,
        showChatPanel,
        revisionCount,
        hasRevisions,
        // Revision actions
        loadRevisions,
        loadRevision,
        restoreRevision,
        toggleRevisions,
        toggleChatPanel,
        clearSelectedRevision,
        $reset,
    };
});
