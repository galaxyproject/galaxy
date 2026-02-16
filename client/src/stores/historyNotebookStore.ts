import { defineStore } from "pinia";
import { computed, ref } from "vue";

import {
    createHistoryNotebook,
    type CreateNotebookPayload,
    deleteHistoryNotebook,
    fetchHistoryNotebook,
    fetchHistoryNotebooks,
    fetchNotebookRevision,
    fetchNotebookRevisions,
    type HistoryNotebookDetails,
    type HistoryNotebookRevisionDetails,
    type HistoryNotebookRevisionSummary,
    type HistoryNotebookSummary,
    revertNotebookRevision,
    updateHistoryNotebook,
    type UpdateNotebookPayload,
} from "@/api/historyNotebooks";
import { useUserLocalStorage } from "@/composables/userLocalStorage";

export const useHistoryNotebookStore = defineStore("historyNotebook", () => {
    const notebooks = ref<HistoryNotebookSummary[]>([]);
    const currentNotebook = ref<HistoryNotebookDetails | null>(null);
    const originalContent = ref("");
    const currentContent = ref("");
    const originalTitle = ref("");
    const currentTitle = ref("");
    const isLoadingList = ref(false);
    const isLoadingNotebook = ref(false);
    const isSaving = ref(false);
    const error = ref<string | null>(null);
    const historyId = ref<string | null>(null);

    // Per-history "current notebook" ID persisted across sessions
    const currentNotebookIds = useUserLocalStorage<Record<string, string>>("history-notebook-current", {});

    // Per-notebook chat exchange ID persisted across panel close/reopen
    const currentChatExchangeIds = useUserLocalStorage<Record<string, number | null>>(
        "history-notebook-chat-exchange",
        {},
    );

    // Per-notebook dismissed proposal message IDs
    const dismissedChatProposals = useUserLocalStorage<Record<string, string[]>>(
        "history-notebook-dismissed-proposals",
        {},
    );

    // Revision state
    const revisions = ref<HistoryNotebookRevisionSummary[]>([]);
    const selectedRevision = ref<HistoryNotebookRevisionDetails | null>(null);
    const isLoadingRevisions = ref(false);
    const isLoadingRevision = ref(false);
    const isReverting = ref(false);
    const showRevisions = ref(false);
    const showChatPanel = ref(false);

    const hasNotebooks = computed(() => notebooks.value.length > 0);
    const hasCurrentNotebook = computed(() => currentNotebook.value !== null);
    const isDirty = computed(
        () => currentContent.value !== originalContent.value || currentTitle.value !== originalTitle.value,
    );
    const canSave = computed(() => isDirty.value && !isSaving.value);
    const revisionCount = computed(() => revisions.value.length);
    const hasRevisions = computed(() => revisions.value.length > 1);

    async function loadNotebooks(newHistoryId: string) {
        historyId.value = newHistoryId;
        isLoadingList.value = true;
        error.value = null;
        try {
            notebooks.value = await fetchHistoryNotebooks(newHistoryId);
        } catch (e: any) {
            error.value = e.message || "Failed to load notebooks";
        } finally {
            isLoadingList.value = false;
        }
    }

    async function loadNotebook(notebookId: string) {
        if (!historyId.value) {
            return;
        }
        isLoadingNotebook.value = true;
        error.value = null;
        try {
            const data = await fetchHistoryNotebook(historyId.value, notebookId);
            currentNotebook.value = data;
            // Use content_editor (raw) for the editor, not content (expanded for rendering)
            const editorContent = data.content_editor ?? data.content ?? "";
            originalContent.value = editorContent;
            currentContent.value = editorContent;
            originalTitle.value = data.title || "";
            currentTitle.value = data.title || "";
            setCurrentNotebookId(historyId.value, notebookId);
        } catch (e: any) {
            error.value = e.message || "Failed to load notebook";
        } finally {
            isLoadingNotebook.value = false;
        }
    }

    async function createNotebook(payload?: Partial<CreateNotebookPayload>): Promise<HistoryNotebookDetails | null> {
        if (!historyId.value) {
            return null;
        }
        isLoadingNotebook.value = true;
        error.value = null;
        try {
            const data = await createHistoryNotebook(historyId.value, {
                content: null,
                content_format: "markdown",
                ...payload,
            });
            currentNotebook.value = data;
            const editorContent = data.content_editor ?? data.content ?? "";
            originalContent.value = editorContent;
            currentContent.value = editorContent;
            originalTitle.value = data.title || "";
            currentTitle.value = data.title || "";
            await loadNotebooks(historyId.value);
            return data;
        } catch (e: any) {
            error.value = e.message || "Failed to create notebook";
            throw e;
        } finally {
            isLoadingNotebook.value = false;
        }
    }

    async function saveNotebook(editSource?: string) {
        if (!historyId.value || !currentNotebook.value || !isDirty.value) {
            return;
        }
        isSaving.value = true;
        error.value = null;
        try {
            const payload: UpdateNotebookPayload = {
                content: currentContent.value,
                content_format: "markdown",
                title: currentTitle.value || undefined,
                edit_source: editSource,
            };
            const data = await updateHistoryNotebook(historyId.value, currentNotebook.value.id, payload);
            currentNotebook.value = data;
            // Use current values (what the user typed) as the baseline, not data values
            // which may be transformed by rewrite_content_for_export for rendering.
            originalContent.value = currentContent.value;
            originalTitle.value = currentTitle.value;
            // Sync the notebooks list so handleSelect reads the updated title (e.g. for WM window titles)
            const idx = notebooks.value.findIndex((n) => n.id === data.id);
            if (idx !== -1) {
                notebooks.value[idx] = {
                    ...notebooks.value[idx]!,
                    title: currentTitle.value,
                    update_time: data.update_time,
                };
            }
        } catch (e: any) {
            error.value = e.message || "Failed to save notebook";
            throw e;
        } finally {
            isSaving.value = false;
        }
    }

    async function deleteCurrentNotebook() {
        if (!historyId.value || !currentNotebook.value) {
            return;
        }
        try {
            const deletedId = currentNotebook.value.id;
            await deleteHistoryNotebook(historyId.value, deletedId);
            clearCurrentNotebookId(historyId.value);
            clearCurrentChatExchangeId(deletedId);
            clearDismissedProposals(deletedId);
            currentNotebook.value = null;
            originalContent.value = "";
            currentContent.value = "";
            originalTitle.value = "";
            currentTitle.value = "";
            await loadNotebooks(historyId.value);
        } catch (e: any) {
            error.value = e.message || "Failed to delete notebook";
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

    function clearCurrentNotebook() {
        const notebookId = currentNotebook.value?.id;
        currentNotebook.value = null;
        originalContent.value = "";
        currentContent.value = "";
        originalTitle.value = "";
        currentTitle.value = "";
        showChatPanel.value = false;
        if (notebookId) {
            clearCurrentChatExchangeId(notebookId);
        }
        clearRevisionState();
    }

    // --- Current notebook resolution ---

    function getCurrentNotebookId(forHistoryId: string): string | null {
        return currentNotebookIds.value[forHistoryId] || null;
    }

    function setCurrentNotebookId(forHistoryId: string, notebookId: string) {
        currentNotebookIds.value = { ...currentNotebookIds.value, [forHistoryId]: notebookId };
    }

    function clearCurrentNotebookId(forHistoryId: string) {
        const { [forHistoryId]: _removed, ...rest } = currentNotebookIds.value;
        currentNotebookIds.value = rest;
    }

    // --- Chat exchange persistence ---

    function getCurrentChatExchangeId(notebookId: string): number | null {
        return currentChatExchangeIds.value[notebookId] ?? null;
    }

    function setCurrentChatExchangeId(notebookId: string, exchangeId: number | null) {
        currentChatExchangeIds.value = { ...currentChatExchangeIds.value, [notebookId]: exchangeId };
    }

    function clearCurrentChatExchangeId(notebookId: string) {
        const { [notebookId]: _removed, ...rest } = currentChatExchangeIds.value;
        currentChatExchangeIds.value = rest;
    }

    // --- Dismissed proposals persistence ---

    function getDismissedProposals(notebookId: string): string[] {
        return dismissedChatProposals.value[notebookId] ?? [];
    }

    function addDismissedProposal(notebookId: string, messageId: string) {
        const current = dismissedChatProposals.value[notebookId] ?? [];
        if (!current.includes(messageId)) {
            dismissedChatProposals.value = {
                ...dismissedChatProposals.value,
                [notebookId]: [...current, messageId],
            };
        }
    }

    function clearDismissedProposals(notebookId: string) {
        const { [notebookId]: _removed, ...rest } = dismissedChatProposals.value;
        dismissedChatProposals.value = rest;
    }

    async function resolveCurrentNotebook(forHistoryId: string): Promise<string> {
        // Always populate the notebooks list so callers can look up titles
        await loadNotebooks(forHistoryId);

        const storedId = getCurrentNotebookId(forHistoryId);
        if (storedId) {
            const exists = notebooks.value.some((n) => n.id === storedId);
            if (exists) {
                return storedId;
            }
            // stale mapping — clear and re-resolve below
            clearCurrentNotebookId(forHistoryId);
        }

        if (notebooks.value.length > 0) {
            const sorted = [...notebooks.value].sort(
                (a, b) => new Date(b.update_time).getTime() - new Date(a.update_time).getTime(),
            );
            const id = sorted[0]!.id;
            setCurrentNotebookId(forHistoryId, id);
            return id;
        }

        // No notebooks exist — create one
        const created = await createHistoryNotebook(forHistoryId, {
            content: null,
            content_format: "markdown",
        });
        setCurrentNotebookId(forHistoryId, created.id);
        return created.id;
    }

    // --- Revision actions ---

    async function loadRevisions() {
        if (!historyId.value || !currentNotebook.value) {
            return;
        }
        isLoadingRevisions.value = true;
        try {
            revisions.value = await fetchNotebookRevisions(historyId.value, currentNotebook.value.id);
        } catch (e: any) {
            error.value = e.message || "Failed to load revisions";
        } finally {
            isLoadingRevisions.value = false;
        }
    }

    async function loadRevision(revisionId: string) {
        if (!historyId.value || !currentNotebook.value) {
            return;
        }
        isLoadingRevision.value = true;
        try {
            selectedRevision.value = await fetchNotebookRevision(historyId.value, currentNotebook.value.id, revisionId);
        } catch (e: any) {
            error.value = e.message || "Failed to load revision";
        } finally {
            isLoadingRevision.value = false;
        }
    }

    async function restoreRevision(revisionId: string) {
        if (!historyId.value || !currentNotebook.value) {
            return;
        }
        isReverting.value = true;
        try {
            const data = await revertNotebookRevision(historyId.value, currentNotebook.value.id, revisionId);
            currentNotebook.value = data;
            const editorContent = data.content_editor ?? data.content ?? "";
            originalContent.value = editorContent;
            currentContent.value = editorContent;
            selectedRevision.value = null;
            showRevisions.value = false;
            await loadRevisions();
        } catch (e: any) {
            error.value = e.message || "Failed to restore revision";
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
    }

    function clearRevisionState() {
        revisions.value = [];
        selectedRevision.value = null;
        isLoadingRevisions.value = false;
        isLoadingRevision.value = false;
        isReverting.value = false;
        showRevisions.value = false;
    }

    /** Reset ephemeral state. Does NOT clear currentNotebookIds (persisted cross-session). */
    function $reset() {
        notebooks.value = [];
        currentNotebook.value = null;
        originalContent.value = "";
        currentContent.value = "";
        originalTitle.value = "";
        currentTitle.value = "";
        isLoadingList.value = false;
        isLoadingNotebook.value = false;
        isSaving.value = false;
        error.value = null;
        historyId.value = null;
        showChatPanel.value = false;
        clearRevisionState();
    }

    return {
        notebooks,
        currentNotebook,
        currentContent,
        currentTitle,
        isLoadingList,
        isLoadingNotebook,
        isSaving,
        error,
        historyId,
        hasNotebooks,
        hasCurrentNotebook,
        isDirty,
        canSave,
        loadNotebooks,
        loadNotebook,
        createNotebook,
        saveNotebook,
        deleteCurrentNotebook,
        updateContent,
        updateTitle,
        discardChanges,
        clearCurrentNotebook,
        // Current notebook resolution
        currentNotebookIds,
        getCurrentNotebookId,
        setCurrentNotebookId,
        clearCurrentNotebookId,
        resolveCurrentNotebook,
        // Chat exchange persistence
        currentChatExchangeIds,
        getCurrentChatExchangeId,
        setCurrentChatExchangeId,
        clearCurrentChatExchangeId,
        // Dismissed proposals persistence
        getDismissedProposals,
        addDismissedProposal,
        clearDismissedProposals,
        // Revision state
        revisions,
        selectedRevision,
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
