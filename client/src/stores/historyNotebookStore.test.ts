import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { HistoryNotebookDetails, HistoryNotebookSummary } from "@/api/historyNotebooks";

import { useHistoryNotebookStore } from "./historyNotebookStore";

const TEST_HISTORY_ID = "abc123historyid";
const TEST_NOTEBOOK_ID = "def456notebookid";
const TEST_REVISION_ID = "rev789revisionid";

const TEST_NOTEBOOK_SUMMARY: HistoryNotebookSummary = {
    id: TEST_NOTEBOOK_ID,
    history_id: TEST_HISTORY_ID,
    title: "My Analysis Notes",
    latest_revision_id: TEST_REVISION_ID,
    revision_ids: [TEST_REVISION_ID],
    deleted: false,
    create_time: "2025-06-15T10:30:00Z",
    update_time: "2025-06-15T12:45:00Z",
};

const TEST_NOTEBOOK_DETAILS: HistoryNotebookDetails = {
    id: TEST_NOTEBOOK_ID,
    history_id: TEST_HISTORY_ID,
    title: "My Analysis Notes",
    latest_revision_id: TEST_REVISION_ID,
    revision_ids: [TEST_REVISION_ID],
    deleted: false,
    create_time: "2025-06-15T10:30:00Z",
    update_time: "2025-06-15T12:45:00Z",
    content: "# Analysis\n\nSome markdown content here.",
    content_format: "markdown",
    edit_source: "user",
};

const { server, http } = useServerMock();

/** Set up default successful handlers for all notebook endpoints. */
function useDefaultHandlers() {
    server.use(
        http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
            return response(200).json([TEST_NOTEBOOK_SUMMARY]);
        }),
        http.get("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
            return response(200).json(TEST_NOTEBOOK_DETAILS);
        }),
        http.post("/api/histories/{history_id}/notebooks", ({ response }) => {
            return response(200).json(TEST_NOTEBOOK_DETAILS);
        }),
        http.put("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
            return response(200).json(TEST_NOTEBOOK_DETAILS);
        }),
        http.delete("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
            return response(204).empty();
        }),
    );
}

describe("useHistoryNotebookStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    describe("computed properties", () => {
        it("hasNotebooks is false when empty", () => {
            const store = useHistoryNotebookStore();
            expect(store.hasNotebooks).toBe(false);
        });

        it("hasNotebooks is true when notebooks exist", () => {
            const store = useHistoryNotebookStore();
            store.notebooks = [TEST_NOTEBOOK_SUMMARY];
            expect(store.hasNotebooks).toBe(true);
        });

        it("hasCurrentNotebook is false when null", () => {
            const store = useHistoryNotebookStore();
            expect(store.hasCurrentNotebook).toBe(false);
        });

        it("hasCurrentNotebook is true when set", () => {
            const store = useHistoryNotebookStore();
            store.currentNotebook = TEST_NOTEBOOK_DETAILS;
            expect(store.hasCurrentNotebook).toBe(true);
        });

        it("isDirty is false initially", () => {
            const store = useHistoryNotebookStore();
            expect(store.isDirty).toBe(false);
        });

        it("isDirty is true when content changed", () => {
            const store = useHistoryNotebookStore();
            store.updateContent("new content");
            expect(store.isDirty).toBe(true);
        });

        it("isDirty is false when content reverted to original", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_NOTEBOOK_ID);
            const originalContent = store.currentContent;

            store.updateContent("something different");
            expect(store.isDirty).toBe(true);

            store.updateContent(originalContent);
            expect(store.isDirty).toBe(false);
        });

        it("canSave is true only when dirty and not saving", () => {
            const store = useHistoryNotebookStore();
            expect(store.canSave).toBe(false);

            store.updateContent("changed");
            expect(store.canSave).toBe(true);
        });

        it("canSave is false when dirty but saving", () => {
            const store = useHistoryNotebookStore();
            store.updateContent("changed");
            // Simulate saving state
            store.$patch({ isSaving: true });
            expect(store.isDirty).toBe(true);
            expect(store.canSave).toBe(false);
        });
    });

    describe("loadNotebooks", () => {
        it("sets historyId and populates notebooks on success", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();

            await store.loadNotebooks(TEST_HISTORY_ID);

            expect(store.historyId).toBe(TEST_HISTORY_ID);
            expect(store.notebooks).toEqual([TEST_NOTEBOOK_SUMMARY]);
        });

        it("sets isLoadingList during load", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();

            const promise = store.loadNotebooks(TEST_HISTORY_ID);
            expect(store.isLoadingList).toBe(true);

            await promise;
            expect(store.isLoadingList).toBe(false);
        });

        it("sets error on API failure", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response("4XX").json({ err_msg: "History not found", err_code: 404 }, { status: 404 });
                }),
            );
            const store = useHistoryNotebookStore();

            await store.loadNotebooks(TEST_HISTORY_ID);

            expect(store.error).toBeTruthy();
            expect(store.isLoadingList).toBe(false);
        });

        it("clears previous error on new load", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response("4XX").json({ err_msg: "History not found", err_code: 404 }, { status: 404 });
                }),
            );
            const store = useHistoryNotebookStore();

            await store.loadNotebooks(TEST_HISTORY_ID);
            expect(store.error).toBeTruthy();

            // Now set up success handler and reload
            server.use(
                http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response(200).json([]);
                }),
            );

            await store.loadNotebooks(TEST_HISTORY_ID);
            expect(store.error).toBeNull();
        });
    });

    describe("loadNotebook", () => {
        it("returns early if no historyId", async () => {
            const store = useHistoryNotebookStore();

            await store.loadNotebook(TEST_NOTEBOOK_ID);

            expect(store.currentNotebook).toBeNull();
            expect(store.isLoadingNotebook).toBe(false);
        });

        it("populates currentNotebook and content on success", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            await store.loadNotebook(TEST_NOTEBOOK_ID);

            expect(store.currentNotebook).toEqual(TEST_NOTEBOOK_DETAILS);
            expect(store.currentContent).toBe(TEST_NOTEBOOK_DETAILS.content);
            expect(store.currentTitle).toBe(TEST_NOTEBOOK_DETAILS.title);
        });

        it("sets originalContent to match currentContent", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            await store.loadNotebook(TEST_NOTEBOOK_ID);

            expect(store.isDirty).toBe(false);
        });

        it("sets isLoadingNotebook during load", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            const promise = store.loadNotebook(TEST_NOTEBOOK_ID);
            expect(store.isLoadingNotebook).toBe(true);

            await promise;
            expect(store.isLoadingNotebook).toBe(false);
        });

        it("sets error on API failure", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response("4XX").json({ err_msg: "Notebook not found", err_code: 404 }, { status: 404 });
                }),
            );
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            await store.loadNotebook(TEST_NOTEBOOK_ID);

            expect(store.error).toBeTruthy();
            expect(store.isLoadingNotebook).toBe(false);
        });
    });

    describe("createNotebook", () => {
        it("returns null if no historyId", async () => {
            const store = useHistoryNotebookStore();

            const result = await store.createNotebook();

            expect(result).toBeNull();
        });

        it("creates notebook, sets as current, refreshes list", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            const result = await store.createNotebook({ title: "New Notebook" });

            expect(result).toEqual(TEST_NOTEBOOK_DETAILS);
            expect(store.currentNotebook).toEqual(TEST_NOTEBOOK_DETAILS);
            expect(store.currentContent).toBe(TEST_NOTEBOOK_DETAILS.content);
            expect(store.currentTitle).toBe(TEST_NOTEBOOK_DETAILS.title);
            expect(store.isDirty).toBe(false);
            // loadNotebooks was called, so notebooks should be populated
            expect(store.notebooks).toEqual([TEST_NOTEBOOK_SUMMARY]);
        });

        it("sets isLoadingNotebook during creation", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            const promise = store.createNotebook();
            expect(store.isLoadingNotebook).toBe(true);

            await promise;
            expect(store.isLoadingNotebook).toBe(false);
        });

        it("sets error and rethrows on failure", async () => {
            server.use(
                http.post("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response("4XX").json({ err_msg: "Cannot create notebook", err_code: 400 }, { status: 400 });
                }),
            );
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            await expect(store.createNotebook()).rejects.toThrow();
            expect(store.error).toBeTruthy();
            expect(store.isLoadingNotebook).toBe(false);
        });
    });

    describe("saveNotebook", () => {
        it("does nothing if not dirty", async () => {
            // Wire up a PUT that would change update_time if called
            const modifiedDetails = { ...TEST_NOTEBOOK_DETAILS, update_time: "2099-01-01T00:00:00Z" };
            server.use(
                http.put("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(200).json(modifiedDetails);
                }),
            );
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            store.currentNotebook = TEST_NOTEBOOK_DETAILS;

            await store.saveNotebook();

            expect(store.isSaving).toBe(false);
            expect(store.error).toBeNull();
            // Notebook should be untouched -- PUT should not have been called
            expect(store.currentNotebook!.update_time).toBe(TEST_NOTEBOOK_DETAILS.update_time);
        });

        it("does nothing if no currentNotebook", async () => {
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            store.updateContent("dirty");

            await store.saveNotebook();

            expect(store.isSaving).toBe(false);
            expect(store.error).toBeNull();
            expect(store.currentNotebook).toBeNull();
        });

        it("does nothing if no historyId", async () => {
            const store = useHistoryNotebookStore();
            store.currentNotebook = TEST_NOTEBOOK_DETAILS;
            store.updateContent("dirty");

            await store.saveNotebook();

            expect(store.isSaving).toBe(false);
            expect(store.error).toBeNull();
        });

        it("updates notebook and resets originalContent on success", async () => {
            const updatedDetails: HistoryNotebookDetails = {
                ...TEST_NOTEBOOK_DETAILS,
                content: "updated content",
                update_time: "2025-06-16T09:00:00Z",
            };
            server.use(
                http.get("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(200).json(TEST_NOTEBOOK_DETAILS);
                }),
                http.put("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(200).json(updatedDetails);
                }),
            );
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            // Load notebook to set originalContent via the store's own logic
            await store.loadNotebook(TEST_NOTEBOOK_ID);
            expect(store.isDirty).toBe(false);

            store.updateContent("updated content");
            expect(store.isDirty).toBe(true);

            await store.saveNotebook();

            expect(store.currentNotebook).toEqual(updatedDetails);
            // originalContent should now match the saved content
            expect(store.isDirty).toBe(false);
        });

        it("sets isSaving during save", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(200).json(TEST_NOTEBOOK_DETAILS);
                }),
                http.put("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(200).json(TEST_NOTEBOOK_DETAILS);
                }),
            );
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_NOTEBOOK_ID);
            store.updateContent("new content");

            const promise = store.saveNotebook();
            expect(store.isSaving).toBe(true);

            await promise;
            expect(store.isSaving).toBe(false);
        });

        it("sets error and rethrows on failure", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(200).json(TEST_NOTEBOOK_DETAILS);
                }),
                http.put("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response("4XX").json({ err_msg: "Notebook is deleted", err_code: 400 }, { status: 400 });
                }),
            );
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_NOTEBOOK_ID);
            store.updateContent("new content");

            await expect(store.saveNotebook()).rejects.toThrow();
            expect(store.error).toBeTruthy();
            expect(store.isSaving).toBe(false);
        });
    });

    describe("deleteCurrentNotebook", () => {
        it("does nothing if no currentNotebook", async () => {
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            await store.deleteCurrentNotebook();

            expect(store.error).toBeNull();
        });

        it("does nothing if no historyId", async () => {
            const store = useHistoryNotebookStore();
            store.currentNotebook = TEST_NOTEBOOK_DETAILS;

            await store.deleteCurrentNotebook();

            // currentNotebook remains since guard exits early
            expect(store.currentNotebook).toEqual(TEST_NOTEBOOK_DETAILS);
        });

        it("clears current state and refreshes list on success", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(200).json(TEST_NOTEBOOK_DETAILS);
                }),
                http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response(200).json([TEST_NOTEBOOK_SUMMARY]);
                }),
                http.delete("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(204).empty();
                }),
            );
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_NOTEBOOK_ID);
            expect(store.currentNotebook).not.toBeNull();

            // Override GET notebooks to return empty after delete
            server.use(
                http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response(200).json([]);
                }),
            );

            await store.deleteCurrentNotebook();

            expect(store.currentNotebook).toBeNull();
            expect(store.currentContent).toBe("");
            expect(store.currentTitle).toBe("");
            expect(store.isDirty).toBe(false);
            // loadNotebooks was called with empty response
            expect(store.notebooks).toEqual([]);
        });

        it("sets error and rethrows on failure", async () => {
            server.use(
                http.delete("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response("4XX").json({ err_msg: "Notebook not found", err_code: 404 }, { status: 404 });
                }),
            );
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            store.currentNotebook = TEST_NOTEBOOK_DETAILS;

            await expect(store.deleteCurrentNotebook()).rejects.toThrow();
            expect(store.error).toBeTruthy();
        });
    });

    describe("resolveCurrentNotebook", () => {
        it("returns stored ID when notebook still exists", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();
            store.setCurrentNotebookId(TEST_HISTORY_ID, TEST_NOTEBOOK_ID);

            const result = await store.resolveCurrentNotebook(TEST_HISTORY_ID);
            expect(result).toBe(TEST_NOTEBOOK_ID);
        });

        it("picks most recent notebook when no stored ID", async () => {
            const older: HistoryNotebookSummary = {
                ...TEST_NOTEBOOK_SUMMARY,
                id: "older-nb",
                update_time: "2025-01-01T00:00:00Z",
            };
            const newer: HistoryNotebookSummary = {
                ...TEST_NOTEBOOK_SUMMARY,
                id: "newer-nb",
                update_time: "2025-06-15T12:45:00Z",
            };
            server.use(
                http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response(200).json([older, newer]);
                }),
            );
            const store = useHistoryNotebookStore();

            const result = await store.resolveCurrentNotebook(TEST_HISTORY_ID);
            expect(result).toBe("newer-nb");
            expect(store.getCurrentNotebookId(TEST_HISTORY_ID)).toBe("newer-nb");
        });

        it("creates notebook when history has none", async () => {
            const createdNotebook: HistoryNotebookDetails = {
                ...TEST_NOTEBOOK_DETAILS,
                id: "created-nb",
            };
            server.use(
                http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response(200).json([]);
                }),
                http.post("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response(200).json(createdNotebook);
                }),
            );
            const store = useHistoryNotebookStore();

            const result = await store.resolveCurrentNotebook(TEST_HISTORY_ID);
            expect(result).toBe("created-nb");
            expect(store.getCurrentNotebookId(TEST_HISTORY_ID)).toBe("created-nb");
        });

        it("re-resolves on 404 (deleted notebook)", async () => {
            const freshNotebook: HistoryNotebookSummary = {
                ...TEST_NOTEBOOK_SUMMARY,
                id: "fresh-nb",
            };
            server.use(
                http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
                    // List no longer contains "deleted-nb"
                    return response(200).json([freshNotebook]);
                }),
            );
            const store = useHistoryNotebookStore();
            store.setCurrentNotebookId(TEST_HISTORY_ID, "deleted-nb");

            const result = await store.resolveCurrentNotebook(TEST_HISTORY_ID);
            expect(result).toBe("fresh-nb");
            expect(store.getCurrentNotebookId(TEST_HISTORY_ID)).toBe("fresh-nb");
        });
    });

    describe("currentNotebookId tracking", () => {
        it("loadNotebook updates stored current ID", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });

            await store.loadNotebook(TEST_NOTEBOOK_ID);

            expect(store.getCurrentNotebookId(TEST_HISTORY_ID)).toBe(TEST_NOTEBOOK_ID);
        });

        it("deleteCurrentNotebook clears stored ID", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(200).json(TEST_NOTEBOOK_DETAILS);
                }),
                http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response(200).json([]);
                }),
                http.delete("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(204).empty();
                }),
            );
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_NOTEBOOK_ID);
            expect(store.getCurrentNotebookId(TEST_HISTORY_ID)).toBe(TEST_NOTEBOOK_ID);

            await store.deleteCurrentNotebook();

            expect(store.getCurrentNotebookId(TEST_HISTORY_ID)).toBeNull();
        });

        it("setCurrentNotebookId and clearCurrentNotebookId work correctly", () => {
            const store = useHistoryNotebookStore();

            store.setCurrentNotebookId("h1", "nb1");
            store.setCurrentNotebookId("h2", "nb2");

            expect(store.getCurrentNotebookId("h1")).toBe("nb1");
            expect(store.getCurrentNotebookId("h2")).toBe("nb2");
            expect(store.getCurrentNotebookId("h3")).toBeNull();

            store.clearCurrentNotebookId("h1");
            expect(store.getCurrentNotebookId("h1")).toBeNull();
            expect(store.getCurrentNotebookId("h2")).toBe("nb2");
        });
    });

    describe("panel toggle mutual exclusion", () => {
        it("toggleChatPanel opens and closes chat", () => {
            const store = useHistoryNotebookStore();
            expect(store.showChatPanel).toBe(false);

            store.toggleChatPanel();
            expect(store.showChatPanel).toBe(true);

            store.toggleChatPanel();
            expect(store.showChatPanel).toBe(false);
        });

        it("toggleChatPanel closes revisions and clears selectedRevision when opening chat", () => {
            const store = useHistoryNotebookStore();
            store.$patch({ showRevisions: true });
            store.selectedRevision = {
                id: "rev-1",
                notebook_id: TEST_NOTEBOOK_ID,
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
            const store = useHistoryNotebookStore();
            store.$patch({ showChatPanel: true, showRevisions: false });

            store.toggleChatPanel();

            expect(store.showChatPanel).toBe(false);
            expect(store.showRevisions).toBe(false);
        });

        it("toggleRevisions closes chat when opening revisions", () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID, showChatPanel: true });
            store.currentNotebook = TEST_NOTEBOOK_DETAILS;

            store.toggleRevisions();

            expect(store.showRevisions).toBe(true);
            expect(store.showChatPanel).toBe(false);
        });

        it("toggleRevisions does not touch chat when closing revisions", () => {
            const store = useHistoryNotebookStore();
            store.$patch({ showRevisions: true, showChatPanel: false });

            store.toggleRevisions();

            expect(store.showRevisions).toBe(false);
            expect(store.showChatPanel).toBe(false);
        });

        it("$reset clears showChatPanel", () => {
            const store = useHistoryNotebookStore();
            store.$patch({ showChatPanel: true });

            store.$reset();

            expect(store.showChatPanel).toBe(false);
        });

        it("clearCurrentNotebook clears showChatPanel", () => {
            const store = useHistoryNotebookStore();
            store.$patch({ showChatPanel: true });

            store.clearCurrentNotebook();

            expect(store.showChatPanel).toBe(false);
        });
    });

    describe("chat exchange persistence", () => {
        it("get/set/clear exchange ID", () => {
            const store = useHistoryNotebookStore();

            expect(store.getCurrentChatExchangeId("nb-1")).toBeNull();

            store.setCurrentChatExchangeId("nb-1", 42);
            expect(store.getCurrentChatExchangeId("nb-1")).toBe(42);

            store.setCurrentChatExchangeId("nb-2", 99);
            expect(store.getCurrentChatExchangeId("nb-2")).toBe(99);

            store.clearCurrentChatExchangeId("nb-1");
            expect(store.getCurrentChatExchangeId("nb-1")).toBeNull();
            expect(store.getCurrentChatExchangeId("nb-2")).toBe(99);
        });

        it("setCurrentChatExchangeId with null stores null", () => {
            const store = useHistoryNotebookStore();
            store.setCurrentChatExchangeId("nb-1", 42);
            store.setCurrentChatExchangeId("nb-1", null);
            expect(store.getCurrentChatExchangeId("nb-1")).toBeNull();
        });

        it("clearCurrentNotebook clears chat exchange ID", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_NOTEBOOK_ID);
            store.setCurrentChatExchangeId(TEST_NOTEBOOK_ID, 55);

            store.clearCurrentNotebook();

            expect(store.getCurrentChatExchangeId(TEST_NOTEBOOK_ID)).toBeNull();
        });

        it("deleteCurrentNotebook clears chat exchange ID", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(200).json(TEST_NOTEBOOK_DETAILS);
                }),
                http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response(200).json([]);
                }),
                http.delete("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(204).empty();
                }),
            );
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_NOTEBOOK_ID);
            store.setCurrentChatExchangeId(TEST_NOTEBOOK_ID, 77);

            await store.deleteCurrentNotebook();

            expect(store.getCurrentChatExchangeId(TEST_NOTEBOOK_ID)).toBeNull();
        });
    });

    describe("synchronous actions", () => {
        it("updateContent updates currentContent", () => {
            const store = useHistoryNotebookStore();
            store.updateContent("hello world");
            expect(store.currentContent).toBe("hello world");
        });

        it("updateTitle updates currentTitle", () => {
            const store = useHistoryNotebookStore();
            store.updateTitle("New Title");
            expect(store.currentTitle).toBe("New Title");
        });

        it("discardChanges resets currentContent to originalContent", async () => {
            const notebookWithContent: HistoryNotebookDetails = {
                ...TEST_NOTEBOOK_DETAILS,
                content: "original content",
            };
            server.use(
                http.get("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response(200).json(notebookWithContent);
                }),
            );
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_NOTEBOOK_ID);
            expect(store.currentContent).toBe("original content");

            store.updateContent("modified");
            expect(store.isDirty).toBe(true);

            store.discardChanges();

            expect(store.currentContent).toBe("original content");
            expect(store.isDirty).toBe(false);
        });

        it("clearCurrentNotebook resets current notebook state", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            await store.loadNotebook(TEST_NOTEBOOK_ID);
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
            const store = useHistoryNotebookStore();
            store.$patch({ historyId: TEST_HISTORY_ID });
            store.notebooks = [TEST_NOTEBOOK_SUMMARY];
            store.currentNotebook = TEST_NOTEBOOK_DETAILS;

            store.clearCurrentNotebook();

            expect(store.historyId).toBe(TEST_HISTORY_ID);
            expect(store.notebooks).toEqual([TEST_NOTEBOOK_SUMMARY]);
        });

        it("$reset resets all state", async () => {
            useDefaultHandlers();
            const store = useHistoryNotebookStore();
            // Populate state via store actions
            await store.loadNotebooks(TEST_HISTORY_ID);
            await store.loadNotebook(TEST_NOTEBOOK_ID);
            store.updateContent("modified");
            store.updateTitle("new title");
            store.$patch({
                isSaving: true,
                error: "some error",
            });

            store.$reset();

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
});
