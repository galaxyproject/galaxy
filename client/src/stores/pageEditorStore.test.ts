import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { HistoryPageDetails, HistoryPageSummary } from "@/api/pages";

import { usePageEditorStore } from "./pageEditorStore";

const TEST_HISTORY_ID = "abc123historyid";
const TEST_PAGE_ID = "def456pageid";
const TEST_REVISION_ID = "rev789revisionid";

const TEST_PAGE_SUMMARY: HistoryPageSummary = {
    id: TEST_PAGE_ID,
    history_id: TEST_HISTORY_ID,
    title: "My Analysis Notes",
    slug: null,
    source_invocation_id: null,
    published: false,
    importable: false,
    deleted: false,
    latest_revision_id: TEST_REVISION_ID,
    revision_ids: [TEST_REVISION_ID],
    create_time: "2025-06-15T10:30:00Z",
    update_time: "2025-06-15T12:45:00Z",
    username: "test",
    email_hash: "",
    author_deleted: false,
    model_class: "Page",
    tags: [],
};

const TEST_PAGE_DETAILS: HistoryPageDetails = {
    ...TEST_PAGE_SUMMARY,
    content: "# Analysis\n\nSome markdown content here.",
    content_editor: "# Analysis\n\nSome markdown content here.",
    content_format: "markdown",
    edit_source: "user",
    annotation: null,
};

const { server, http } = useServerMock();

/** Set up default successful handlers for all page endpoints. */
function useDefaultHandlers() {
    server.use(
        http.get("/api/pages", ({ response }) => {
            return response(200).json([TEST_PAGE_SUMMARY]);
        }) as any,
        http.get("/api/pages/:id", ({ response }) => {
            return response(200).json(TEST_PAGE_DETAILS);
        }) as any,
        http.post("/api/pages", ({ response }) => {
            return response(200).json(TEST_PAGE_DETAILS);
        }) as any,
        http.put("/api/pages/:id", ({ response }) => {
            return response(200).json(TEST_PAGE_DETAILS);
        }) as any,
        http.delete("/api/pages/:id", ({ response }) => {
            return response(204).empty();
        }) as any,
    );
}

describe("usePageEditorStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    describe("computed properties", () => {
        it("hasNotebooks is false when empty", () => {
            const store = usePageEditorStore();
            expect(store.hasNotebooks).toBe(false);
        });

        it("hasNotebooks is true when notebooks exist", () => {
            const store = usePageEditorStore();
            store.notebooks = [TEST_PAGE_SUMMARY];
            expect(store.hasNotebooks).toBe(true);
        });

        it("hasCurrentNotebook is false when null", () => {
            const store = usePageEditorStore();
            expect(store.hasCurrentNotebook).toBe(false);
        });

        it("hasCurrentNotebook is true when set", () => {
            const store = usePageEditorStore();
            store.currentNotebook = TEST_PAGE_DETAILS;
            expect(store.hasCurrentNotebook).toBe(true);
        });

        it("isDirty is false initially", () => {
            const store = usePageEditorStore();
            expect(store.isDirty).toBe(false);
        });

        it("isDirty is true when content changed", () => {
            const store = usePageEditorStore();
            store.updateContent("new content");
            expect(store.isDirty).toBe(true);
        });

        it("isDirty is false when content reverted to original", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_PAGE_ID);
            const originalContent = store.currentContent;

            store.updateContent("something different");
            expect(store.isDirty).toBe(true);

            store.updateContent(originalContent);
            expect(store.isDirty).toBe(false);
        });

        it("canSave is true only when dirty and not saving", () => {
            const store = usePageEditorStore();
            expect(store.canSave).toBe(false);

            store.updateContent("changed");
            expect(store.canSave).toBe(true);
        });

        it("canSave is false when dirty but saving", () => {
            const store = usePageEditorStore();
            store.updateContent("changed");
            store.$patch({ isSaving: true });
            expect(store.isDirty).toBe(true);
            expect(store.canSave).toBe(false);
        });
    });

    describe("loadNotebooks", () => {
        it("sets historyId and populates notebooks on success", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();

            await store.loadNotebooks(TEST_HISTORY_ID);

            expect(store.historyId).toBe(TEST_HISTORY_ID);
            expect(store.notebooks).toEqual([TEST_PAGE_SUMMARY]);
        });

        it("sets isLoadingList during load", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();

            const promise = store.loadNotebooks(TEST_HISTORY_ID);
            expect(store.isLoadingList).toBe(true);

            await promise;
            expect(store.isLoadingList).toBe(false);
        });

        it("sets error on API failure", async () => {
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "History not found", err_code: 404 }, { status: 404 });
                }) as any,
            );
            const store = usePageEditorStore();

            await store.loadNotebooks(TEST_HISTORY_ID);

            expect(store.error).toBeTruthy();
            expect(store.isLoadingList).toBe(false);
        });

        it("clears previous error on new load", async () => {
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "History not found", err_code: 404 }, { status: 404 });
                }) as any,
            );
            const store = usePageEditorStore();

            await store.loadNotebooks(TEST_HISTORY_ID);
            expect(store.error).toBeTruthy();

            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response(200).json([]);
                }) as any,
            );

            await store.loadNotebooks(TEST_HISTORY_ID);
            expect(store.error).toBeNull();
        });
    });

    describe("loadNotebook", () => {
        it("returns early if no historyId", async () => {
            const store = usePageEditorStore();

            await store.loadNotebook(TEST_PAGE_ID);

            expect(store.currentNotebook).toBeNull();
            expect(store.isLoadingNotebook).toBe(false);
        });

        it("populates currentNotebook and content on success", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            await store.loadNotebook(TEST_PAGE_ID);

            expect(store.currentNotebook).toEqual(TEST_PAGE_DETAILS);
            expect(store.currentContent).toBe(TEST_PAGE_DETAILS.content);
            expect(store.currentTitle).toBe(TEST_PAGE_DETAILS.title);
        });

        it("sets originalContent to match currentContent", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            await store.loadNotebook(TEST_PAGE_ID);

            expect(store.isDirty).toBe(false);
        });

        it("sets isLoadingNotebook during load", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            const promise = store.loadNotebook(TEST_PAGE_ID);
            expect(store.isLoadingNotebook).toBe(true);

            await promise;
            expect(store.isLoadingNotebook).toBe(false);
        });

        it("sets error on API failure", async () => {
            server.use(
                http.get("/api/pages/:id", ({ response }) => {
                    return response("4XX").json({ err_msg: "Page not found", err_code: 404 }, { status: 404 });
                }) as any,
            );
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            await store.loadNotebook(TEST_PAGE_ID);

            expect(store.error).toBeTruthy();
            expect(store.isLoadingNotebook).toBe(false);
        });
    });

    describe("createNotebook", () => {
        it("returns null if no historyId", async () => {
            const store = usePageEditorStore();

            const result = await store.createNotebook();

            expect(result).toBeNull();
        });

        it("creates page, sets as current, refreshes list", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            const result = await store.createNotebook({ title: "New Page" });

            expect(result).toEqual(TEST_PAGE_DETAILS);
            expect(store.currentNotebook).toEqual(TEST_PAGE_DETAILS);
            expect(store.currentContent).toBe(TEST_PAGE_DETAILS.content);
            expect(store.currentTitle).toBe(TEST_PAGE_DETAILS.title);
            expect(store.isDirty).toBe(false);
            expect(store.notebooks).toEqual([TEST_PAGE_SUMMARY]);
        });

        it("sets isLoadingNotebook during creation", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            const promise = store.createNotebook();
            expect(store.isLoadingNotebook).toBe(true);

            await promise;
            expect(store.isLoadingNotebook).toBe(false);
        });

        it("sets error and rethrows on failure", async () => {
            server.use(
                http.post("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "Cannot create page", err_code: 400 }, { status: 400 });
                }) as any,
            );
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            await expect(store.createNotebook()).rejects.toThrow();
            expect(store.error).toBeTruthy();
            expect(store.isLoadingNotebook).toBe(false);
        });
    });

    describe("saveNotebook", () => {
        it("does nothing if not dirty", async () => {
            const modifiedDetails = { ...TEST_PAGE_DETAILS, update_time: "2099-01-01T00:00:00Z" };
            server.use(
                http.put("/api/pages/:id", ({ response }) => {
                    return response(200).json(modifiedDetails);
                }) as any,
            );
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            store.currentNotebook = TEST_PAGE_DETAILS;

            await store.saveNotebook();

            expect(store.isSaving).toBe(false);
            expect(store.error).toBeNull();
            expect(store.currentNotebook!.update_time).toBe(TEST_PAGE_DETAILS.update_time);
        });

        it("does nothing if no currentNotebook", async () => {
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            store.updateContent("dirty");

            await store.saveNotebook();

            expect(store.isSaving).toBe(false);
            expect(store.error).toBeNull();
            expect(store.currentNotebook).toBeNull();
        });

        it("saves in standalone mode without historyId", async () => {
            server.use(
                http.put("/api/pages/:id", ({ response }) => {
                    return response(200).json({
                        ...TEST_PAGE_DETAILS,
                        content: "dirty",
                        edit_source: "user",
                    });
                }) as any,
            );
            const store = usePageEditorStore();
            store.mode = "standalone";
            store.currentNotebook = TEST_PAGE_DETAILS;
            store.updateContent("dirty");

            await store.saveNotebook();

            expect(store.isSaving).toBe(false);
            expect(store.error).toBeNull();
        });

        it("updates page and resets originalContent on success", async () => {
            const updatedDetails: HistoryPageDetails = {
                ...TEST_PAGE_DETAILS,
                content: "updated content",
                update_time: "2025-06-16T09:00:00Z",
            };
            server.use(
                http.get("/api/pages/:id", ({ response }) => {
                    return response(200).json(TEST_PAGE_DETAILS);
                }) as any,
                http.put("/api/pages/:id", ({ response }) => {
                    return response(200).json(updatedDetails);
                }) as any,
            );
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_PAGE_ID);
            expect(store.isDirty).toBe(false);

            store.updateContent("updated content");
            expect(store.isDirty).toBe(true);

            await store.saveNotebook();

            expect(store.currentNotebook).toEqual(updatedDetails);
            expect(store.isDirty).toBe(false);
        });

        it("sets isSaving during save", async () => {
            server.use(
                http.get("/api/pages/:id", ({ response }) => {
                    return response(200).json(TEST_PAGE_DETAILS);
                }) as any,
                http.put("/api/pages/:id", ({ response }) => {
                    return response(200).json(TEST_PAGE_DETAILS);
                }) as any,
            );
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_PAGE_ID);
            store.updateContent("new content");

            const promise = store.saveNotebook();
            expect(store.isSaving).toBe(true);

            await promise;
            expect(store.isSaving).toBe(false);
        });

        it("sets error and rethrows on failure", async () => {
            server.use(
                http.get("/api/pages/:id", ({ response }) => {
                    return response(200).json(TEST_PAGE_DETAILS);
                }) as any,
                http.put("/api/pages/:id", ({ response }) => {
                    return response("4XX").json({ err_msg: "Page is deleted", err_code: 400 }, { status: 400 });
                }) as any,
            );
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_PAGE_ID);
            store.updateContent("new content");

            await expect(store.saveNotebook()).rejects.toThrow();
            expect(store.error).toBeTruthy();
            expect(store.isSaving).toBe(false);
        });
    });

    describe("deleteCurrentNotebook", () => {
        it("does nothing if no currentNotebook", async () => {
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            await store.deleteCurrentNotebook();

            expect(store.error).toBeNull();
        });

        it("does nothing if no historyId", async () => {
            const store = usePageEditorStore();
            store.currentNotebook = TEST_PAGE_DETAILS;

            await store.deleteCurrentNotebook();

            expect(store.currentNotebook).toEqual(TEST_PAGE_DETAILS);
        });

        it("clears current state and refreshes list on success", async () => {
            server.use(
                http.get("/api/pages/:id", ({ response }) => {
                    return response(200).json(TEST_PAGE_DETAILS);
                }) as any,
                http.get("/api/pages", ({ response }) => {
                    return response(200).json([TEST_PAGE_SUMMARY]);
                }) as any,
                http.delete("/api/pages/:id", ({ response }) => {
                    return response(204).empty();
                }) as any,
            );
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_PAGE_ID);
            expect(store.currentNotebook).not.toBeNull();

            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response(200).json([]);
                }) as any,
            );

            await store.deleteCurrentNotebook();

            expect(store.currentNotebook).toBeNull();
            expect(store.currentContent).toBe("");
            expect(store.currentTitle).toBe("");
            expect(store.isDirty).toBe(false);
            expect(store.notebooks).toEqual([]);
        });

        it("sets error and rethrows on failure", async () => {
            server.use(
                http.delete("/api/pages/:id", ({ response }) => {
                    return response("4XX").json({ err_msg: "Page not found", err_code: 404 }, { status: 404 });
                }) as any,
            );
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            store.currentNotebook = TEST_PAGE_DETAILS;

            await expect(store.deleteCurrentNotebook()).rejects.toThrow();
            expect(store.error).toBeTruthy();
        });
    });

    describe("resolveCurrentNotebook", () => {
        it("returns stored ID when page still exists", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();
            store.setCurrentNotebookId(TEST_HISTORY_ID, TEST_PAGE_ID);

            const result = await store.resolveCurrentNotebook(TEST_HISTORY_ID);
            expect(result).toBe(TEST_PAGE_ID);
        });

        it("picks most recent page when no stored ID", async () => {
            const older: HistoryPageSummary = {
                ...TEST_PAGE_SUMMARY,
                id: "older-page",
                update_time: "2025-01-01T00:00:00Z",
            };
            const newer: HistoryPageSummary = {
                ...TEST_PAGE_SUMMARY,
                id: "newer-page",
                update_time: "2025-06-15T12:45:00Z",
            };
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response(200).json([older, newer]);
                }) as any,
            );
            const store = usePageEditorStore();

            const result = await store.resolveCurrentNotebook(TEST_HISTORY_ID);
            expect(result).toBe("newer-page");
            expect(store.getCurrentNotebookId(TEST_HISTORY_ID)).toBe("newer-page");
        });

        it("creates page when history has none", async () => {
            const createdPage: HistoryPageDetails = {
                ...TEST_PAGE_DETAILS,
                id: "created-page",
            };
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response(200).json([]);
                }) as any,
                http.post("/api/pages", ({ response }) => {
                    return response(200).json(createdPage);
                }) as any,
            );
            const store = usePageEditorStore();

            const result = await store.resolveCurrentNotebook(TEST_HISTORY_ID);
            expect(result).toBe("created-page");
            expect(store.getCurrentNotebookId(TEST_HISTORY_ID)).toBe("created-page");
        });

        it("re-resolves on stale mapping (deleted page)", async () => {
            const freshPage: HistoryPageSummary = {
                ...TEST_PAGE_SUMMARY,
                id: "fresh-page",
            };
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response(200).json([freshPage]);
                }) as any,
            );
            const store = usePageEditorStore();
            store.setCurrentNotebookId(TEST_HISTORY_ID, "deleted-page");

            const result = await store.resolveCurrentNotebook(TEST_HISTORY_ID);
            expect(result).toBe("fresh-page");
            expect(store.getCurrentNotebookId(TEST_HISTORY_ID)).toBe("fresh-page");
        });
    });

    describe("currentNotebookId tracking", () => {
        it("loadNotebook updates stored current ID", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            await store.loadNotebook(TEST_PAGE_ID);

            expect(store.getCurrentNotebookId(TEST_HISTORY_ID)).toBe(TEST_PAGE_ID);
        });

        it("deleteCurrentNotebook clears stored ID", async () => {
            server.use(
                http.get("/api/pages/:id", ({ response }) => {
                    return response(200).json(TEST_PAGE_DETAILS);
                }) as any,
                http.get("/api/pages", ({ response }) => {
                    return response(200).json([]);
                }) as any,
                http.delete("/api/pages/:id", ({ response }) => {
                    return response(204).empty();
                }) as any,
            );
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_PAGE_ID);
            expect(store.getCurrentNotebookId(TEST_HISTORY_ID)).toBe(TEST_PAGE_ID);

            await store.deleteCurrentNotebook();

            expect(store.getCurrentNotebookId(TEST_HISTORY_ID)).toBeNull();
        });

        it("setCurrentNotebookId and clearCurrentNotebookId work correctly", () => {
            const store = usePageEditorStore();

            store.setCurrentNotebookId("h1", "p1");
            store.setCurrentNotebookId("h2", "p2");

            expect(store.getCurrentNotebookId("h1")).toBe("p1");
            expect(store.getCurrentNotebookId("h2")).toBe("p2");
            expect(store.getCurrentNotebookId("h3")).toBeNull();

            store.clearCurrentNotebookId("h1");
            expect(store.getCurrentNotebookId("h1")).toBeNull();
            expect(store.getCurrentNotebookId("h2")).toBe("p2");
        });
    });

    describe("panel toggle mutual exclusion", () => {
        it("toggleChatPanel opens and closes chat", () => {
            const store = usePageEditorStore();
            expect(store.showChatPanel).toBe(false);

            store.toggleChatPanel();
            expect(store.showChatPanel).toBe(true);

            store.toggleChatPanel();
            expect(store.showChatPanel).toBe(false);
        });

        it("toggleChatPanel closes revisions and clears selectedRevision when opening chat", () => {
            const store = usePageEditorStore();
            store.$patch({ showRevisions: true });
            store.selectedRevision = {
                id: "rev-1",
                page_id: TEST_PAGE_ID,
                content: "# Old",
                content_format: "markdown",
                edit_source: "user",
                create_time: "2024-01-01T00:00:00",
                update_time: "2024-01-01T00:00:00",
            } as any;

            store.toggleChatPanel();

            expect(store.showChatPanel).toBe(true);
            expect(store.showRevisions).toBe(false);
            expect(store.selectedRevision).toBeNull();
        });

        it("toggleChatPanel does not touch revisions when closing chat", () => {
            const store = usePageEditorStore();
            store.$patch({ showChatPanel: true, showRevisions: false });

            store.toggleChatPanel();

            expect(store.showChatPanel).toBe(false);
            expect(store.showRevisions).toBe(false);
        });

        it("toggleRevisions closes chat when opening revisions", () => {
            useDefaultHandlers();
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID, showChatPanel: true });
            store.currentNotebook = TEST_PAGE_DETAILS;

            store.toggleRevisions();

            expect(store.showRevisions).toBe(true);
            expect(store.showChatPanel).toBe(false);
        });

        it("toggleRevisions does not touch chat when closing revisions", () => {
            const store = usePageEditorStore();
            store.$patch({ showRevisions: true, showChatPanel: false });

            store.toggleRevisions();

            expect(store.showRevisions).toBe(false);
            expect(store.showChatPanel).toBe(false);
        });

        it("$reset clears showChatPanel", () => {
            const store = usePageEditorStore();
            store.$patch({ showChatPanel: true });

            store.$reset();

            expect(store.showChatPanel).toBe(false);
        });

        it("clearCurrentNotebook clears showChatPanel", () => {
            const store = usePageEditorStore();
            store.$patch({ showChatPanel: true });

            store.clearCurrentNotebook();

            expect(store.showChatPanel).toBe(false);
        });
    });

    describe("chat exchange persistence", () => {
        it("get/set/clear exchange ID", () => {
            const store = usePageEditorStore();

            expect(store.getCurrentChatExchangeId("p-1")).toBeNull();

            store.setCurrentChatExchangeId("p-1", 42);
            expect(store.getCurrentChatExchangeId("p-1")).toBe(42);

            store.setCurrentChatExchangeId("p-2", 99);
            expect(store.getCurrentChatExchangeId("p-2")).toBe(99);

            store.clearCurrentChatExchangeId("p-1");
            expect(store.getCurrentChatExchangeId("p-1")).toBeNull();
            expect(store.getCurrentChatExchangeId("p-2")).toBe(99);
        });

        it("setCurrentChatExchangeId with null stores null", () => {
            const store = usePageEditorStore();
            store.setCurrentChatExchangeId("p-1", 42);
            store.setCurrentChatExchangeId("p-1", null);
            expect(store.getCurrentChatExchangeId("p-1")).toBeNull();
        });

        it("clearCurrentNotebook clears chat exchange ID", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_PAGE_ID);
            store.setCurrentChatExchangeId(TEST_PAGE_ID, 55);

            store.clearCurrentNotebook();

            expect(store.getCurrentChatExchangeId(TEST_PAGE_ID)).toBeNull();
        });

        it("deleteCurrentNotebook clears chat exchange ID", async () => {
            server.use(
                http.get("/api/pages/:id", ({ response }) => {
                    return response(200).json(TEST_PAGE_DETAILS);
                }) as any,
                http.get("/api/pages", ({ response }) => {
                    return response(200).json([]);
                }) as any,
                http.delete("/api/pages/:id", ({ response }) => {
                    return response(204).empty();
                }) as any,
            );
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_PAGE_ID);
            store.setCurrentChatExchangeId(TEST_PAGE_ID, 77);

            await store.deleteCurrentNotebook();

            expect(store.getCurrentChatExchangeId(TEST_PAGE_ID)).toBeNull();
        });
    });

    describe("synchronous actions", () => {
        it("updateContent updates currentContent", () => {
            const store = usePageEditorStore();
            store.updateContent("hello world");
            expect(store.currentContent).toBe("hello world");
        });

        it("updateTitle updates currentTitle", () => {
            const store = usePageEditorStore();
            store.updateTitle("New Title");
            expect(store.currentTitle).toBe("New Title");
        });

        it("discardChanges resets currentContent to originalContent", async () => {
            const pageWithContent: HistoryPageDetails = {
                ...TEST_PAGE_DETAILS,
                content: "original content",
                content_editor: "original content",
            };
            server.use(
                http.get("/api/pages/:id", ({ response }) => {
                    return response(200).json(pageWithContent);
                }) as any,
            );
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_PAGE_ID);
            expect(store.currentContent).toBe("original content");

            store.updateContent("modified");
            expect(store.isDirty).toBe(true);

            store.discardChanges();

            expect(store.currentContent).toBe("original content");
            expect(store.isDirty).toBe(false);
        });

        it("clearCurrentNotebook resets current notebook state", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_PAGE_ID);
            store.updateContent("modified");
            expect(store.currentNotebook).not.toBeNull();
            expect(store.isDirty).toBe(true);

            store.clearCurrentNotebook();

            expect(store.currentNotebook).toBeNull();
            expect(store.currentContent).toBe("");
            expect(store.currentTitle).toBe("");
            expect(store.isDirty).toBe(false);
        });

        it("clearCurrentNotebook does not affect notebooks list or historyId", () => {
            const store = usePageEditorStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            store.notebooks = [TEST_PAGE_SUMMARY];
            store.currentNotebook = TEST_PAGE_DETAILS;

            store.clearCurrentNotebook();

            expect(store.historyId).toBe(TEST_HISTORY_ID);
            expect(store.notebooks).toEqual([TEST_PAGE_SUMMARY]);
        });

        it("$reset resets all state including mode", async () => {
            useDefaultHandlers();
            const store = usePageEditorStore();
            store.mode = "standalone";
            await store.loadNotebooks(TEST_HISTORY_ID);
            await store.loadNotebook(TEST_PAGE_ID);
            store.updateContent("modified");
            store.updateTitle("new title");
            store.$patch({
                isSaving: true,
                error: "some error",
            });

            store.$reset();

            expect(store.mode).toBe("history");
            expect(store.notebooks).toEqual([]);
            expect(store.currentNotebook).toBeNull();
            expect(store.currentContent).toBe("");
            expect(store.currentTitle).toBe("");
            expect(store.isDirty).toBe(false);
            expect(store.isLoadingList).toBe(false);
            expect(store.isLoadingNotebook).toBe(false);
            expect(store.isSaving).toBe(false);
            expect(store.error).toBeNull();
            expect(store.historyId).toBeNull();
        });
    });

    describe("standalone mode", () => {
        const STANDALONE_PAGE: HistoryPageDetails = {
            ...TEST_PAGE_DETAILS,
            history_id: null,
        };

        it("loadPage loads a standalone page without historyId", async () => {
            server.use(
                http.get("/api/pages/:id", ({ response }) => {
                    return response(200).json(STANDALONE_PAGE);
                }) as any,
            );
            const store = usePageEditorStore();
            store.mode = "standalone";

            await store.loadPage(TEST_PAGE_ID);

            expect(store.currentNotebook).toEqual(STANDALONE_PAGE);
            expect(store.currentContent).toBe(STANDALONE_PAGE.content_editor);
            expect(store.historyId).toBeNull();
        });

        it("saveNotebook in standalone mode defaults edit_source to user", async () => {
            let capturedBody: any = null;
            server.use(
                http.put("/api/pages/:id", async ({ request, response }) => {
                    capturedBody = await request.json();
                    return response(200).json(STANDALONE_PAGE);
                }) as any,
            );
            const store = usePageEditorStore();
            store.mode = "standalone";
            store.currentNotebook = STANDALONE_PAGE;
            store.updateContent("new content");

            await store.saveNotebook();

            expect(capturedBody.edit_source).toBe("user");
        });

        it("loadRevisions works without historyId", async () => {
            const revisions = [
                {
                    id: "rev-1",
                    page_id: TEST_PAGE_ID,
                    edit_source: "user",
                    create_time: "2025-01-01",
                    update_time: "2025-01-01",
                },
                {
                    id: "rev-2",
                    page_id: TEST_PAGE_ID,
                    edit_source: "user",
                    create_time: "2025-01-02",
                    update_time: "2025-01-02",
                },
            ];
            server.use(
                http.get("/api/pages/:id/revisions", ({ response }) => {
                    return response(200).json(revisions);
                }) as any,
            );
            const store = usePageEditorStore();
            store.mode = "standalone";
            store.currentNotebook = STANDALONE_PAGE;

            await store.loadRevisions();

            expect(store.revisions).toHaveLength(2);
            expect(store.revisions[0]!.id).toBe("rev-1");
        });

        it("restoreRevision works without historyId", async () => {
            const restoredRevision = {
                id: "rev-new",
                page_id: TEST_PAGE_ID,
                edit_source: "restore",
                create_time: "2025-01-03",
                update_time: "2025-01-03",
            };
            server.use(
                http.post("/api/pages/:id/revisions/:revisionId/revert", ({ response }) => {
                    return response(200).json(restoredRevision);
                }) as any,
                http.get("/api/pages/:id", ({ response }) => {
                    return response(200).json(STANDALONE_PAGE);
                }) as any,
                http.get("/api/pages/:id/revisions", ({ response }) => {
                    return response(200).json([restoredRevision]);
                }) as any,
            );
            const store = usePageEditorStore();
            store.mode = "standalone";
            store.currentNotebook = STANDALONE_PAGE;

            await store.restoreRevision("rev-1");

            expect(store.selectedRevision).toBeNull();
            expect(store.showRevisions).toBe(false);
        });
    });
});
