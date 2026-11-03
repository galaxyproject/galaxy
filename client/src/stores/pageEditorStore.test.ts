import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type {
    HistoryPageDetails,
    HistoryPageSummary,
    PageRevisionDetails,
    PageRevisionSummary,
    UpdateHistoryPagePayload,
} from "@/api/pages";

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

function createHistoryEditorStore() {
    const store = usePageEditorStore();
    store.setCurrentContext(TEST_HISTORY_ID);
    return store;
}

function createRevisionSummary(overrides: Partial<PageRevisionSummary> = {}): PageRevisionSummary {
    return {
        id: "rev-1",
        page_id: TEST_PAGE_ID,
        edit_source: "user",
        create_time: "2025-01-01",
        update_time: "2025-01-01",
        ...overrides,
    };
}

function createRevisionDetails(overrides: Partial<PageRevisionDetails> = {}): PageRevisionDetails {
    return {
        ...createRevisionSummary(),
        content: "",
        content_editor: "",
        content_format: "markdown",
        ...overrides,
    };
}

function pageListHandler(pages: HistoryPageSummary[] = [TEST_PAGE_SUMMARY]) {
    return http.get("/api/pages", ({ response }) => response(200).json(pages));
}

function pageDetailsHandler(page: HistoryPageDetails = TEST_PAGE_DETAILS) {
    return http.get("/api/pages/{id}", ({ response }) => response(200).json(page));
}

describe("usePageEditorStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    describe("page availability and unsaved changes", () => {
        it("hasPages is false when empty", () => {
            const store = usePageEditorStore();
            expect(store.hasPages).toBe(false);
        });

        it("hasPages is true when pages exist", () => {
            const store = usePageEditorStore();
            store.pages = [TEST_PAGE_SUMMARY];
            expect(store.hasPages).toBe(true);
        });

        it("hasCurrentPage is false when null", () => {
            const store = usePageEditorStore();
            expect(store.hasCurrentPage).toBe(false);
        });

        it("hasCurrentPage is true when set", () => {
            const store = usePageEditorStore();
            store.currentPage = TEST_PAGE_DETAILS;
            expect(store.hasCurrentPage).toBe(true);
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
            server.use(pageDetailsHandler());
            const store = createHistoryEditorStore();
            await store.loadPageById(TEST_PAGE_ID);
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

    describe("loadPages", () => {
        it("sets historyId and populates pages on success", async () => {
            server.use(pageListHandler());
            const store = usePageEditorStore();

            await store.loadPages(TEST_HISTORY_ID);

            expect(store.historyId).toBe(TEST_HISTORY_ID);
            expect(store.pages).toEqual([TEST_PAGE_SUMMARY]);
        });

        it("sets isLoadingList during load", async () => {
            server.use(pageListHandler());
            const store = usePageEditorStore();

            const promise = store.loadPages(TEST_HISTORY_ID);
            expect(store.isLoadingList).toBe(true);

            await promise;
            expect(store.isLoadingList).toBe(false);
        });

        it("sets error on API failure", async () => {
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "History not found", err_code: 404 }, { status: 404 });
                }),
            );
            const store = usePageEditorStore();

            await store.loadPages(TEST_HISTORY_ID);

            expect(store.error).toBeTruthy();
            expect(store.isLoadingList).toBe(false);
        });

        it("clears previous error on new load", async () => {
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "History not found", err_code: 404 }, { status: 404 });
                }),
            );
            const store = usePageEditorStore();

            await store.loadPages(TEST_HISTORY_ID);
            expect(store.error).toBeTruthy();

            server.use(pageListHandler([]));

            await store.loadPages(TEST_HISTORY_ID);
            expect(store.error).toBeNull();
        });
    });

    describe("loadPageById", () => {
        it("returns early if no historyId", async () => {
            const store = usePageEditorStore();

            await store.loadPageById(TEST_PAGE_ID);

            expect(store.currentPage).toBeNull();
            expect(store.isLoadingPage).toBe(false);
        });

        it("populates currentPage and content on success", async () => {
            server.use(pageDetailsHandler());
            const store = createHistoryEditorStore();

            await store.loadPageById(TEST_PAGE_ID);

            expect(store.currentPage).toEqual(TEST_PAGE_DETAILS);
            expect(store.currentContent).toBe(TEST_PAGE_DETAILS.content);
            expect(store.currentTitle).toBe(TEST_PAGE_DETAILS.title);
        });

        it("starts with no unsaved changes after loading a page", async () => {
            server.use(pageDetailsHandler());
            const store = createHistoryEditorStore();

            await store.loadPageById(TEST_PAGE_ID);

            expect(store.isDirty).toBe(false);
        });

        it("sets isLoadingPage during load", async () => {
            server.use(pageDetailsHandler());
            const store = createHistoryEditorStore();

            const promise = store.loadPageById(TEST_PAGE_ID);
            expect(store.isLoadingPage).toBe(true);

            await promise;
            expect(store.isLoadingPage).toBe(false);
        });

        it("sets error on API failure", async () => {
            server.use(
                http.get("/api/pages/{id}", ({ response }) => {
                    return response("4XX").json({ err_msg: "Page not found", err_code: 404 }, { status: 404 });
                }),
            );
            const store = createHistoryEditorStore();

            await store.loadPageById(TEST_PAGE_ID);

            expect(store.error).toBeTruthy();
            expect(store.isLoadingPage).toBe(false);
        });
    });

    describe("createPage", () => {
        it("returns null if no historyId", async () => {
            const store = usePageEditorStore();

            const result = await store.createPage();

            expect(result).toBeNull();
        });

        it("creates page, sets as current, refreshes list", async () => {
            server.use(
                pageListHandler(),
                http.post("/api/pages", ({ response }) => response(200).json(TEST_PAGE_DETAILS)),
            );
            const store = createHistoryEditorStore();

            const result = await store.createPage({ title: "New Page" });

            expect(result).toEqual(TEST_PAGE_DETAILS);
            expect(store.currentPage).toEqual(TEST_PAGE_DETAILS);
            expect(store.currentContent).toBe(TEST_PAGE_DETAILS.content);
            expect(store.currentTitle).toBe(TEST_PAGE_DETAILS.title);
            expect(store.isDirty).toBe(false);
            expect(store.pages).toEqual([TEST_PAGE_SUMMARY]);
        });

        it("sets isLoadingPage during creation", async () => {
            server.use(
                pageListHandler(),
                http.post("/api/pages", ({ response }) => response(200).json(TEST_PAGE_DETAILS)),
            );
            const store = createHistoryEditorStore();

            const promise = store.createPage();
            expect(store.isLoadingPage).toBe(true);

            await promise;
            expect(store.isLoadingPage).toBe(false);
        });

        it("sets error and rethrows on failure", async () => {
            server.use(
                http.post("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "Cannot create page", err_code: 400 }, { status: 400 });
                }),
            );
            const store = createHistoryEditorStore();

            await expect(store.createPage()).rejects.toThrow();
            expect(store.error).toBeTruthy();
            expect(store.isLoadingPage).toBe(false);
        });
    });

    describe("savePage", () => {
        it("does nothing if not dirty", async () => {
            const modifiedDetails = { ...TEST_PAGE_DETAILS, update_time: "2099-01-01T00:00:00Z" };
            server.use(
                http.put("/api/pages/{id}", ({ response }) => {
                    return response(200).json(modifiedDetails);
                }),
            );
            const store = createHistoryEditorStore();
            store.currentPage = TEST_PAGE_DETAILS;

            await store.savePage();

            expect(store.isSaving).toBe(false);
            expect(store.error).toBeNull();
            expect(store.currentPage!.update_time).toBe(TEST_PAGE_DETAILS.update_time);
        });

        it("does nothing if no currentPage", async () => {
            const store = createHistoryEditorStore();
            store.updateContent("dirty");

            await store.savePage();

            expect(store.isSaving).toBe(false);
            expect(store.error).toBeNull();
            expect(store.currentPage).toBeNull();
        });

        it("saves in standalone mode without historyId", async () => {
            server.use(
                http.put("/api/pages/{id}", ({ response }) => {
                    return response(200).json({
                        ...TEST_PAGE_DETAILS,
                        content: "dirty",
                        edit_source: "user",
                    });
                }),
            );
            const store = usePageEditorStore();
            store.mode = "standalone";
            store.currentPage = TEST_PAGE_DETAILS;
            store.updateContent("dirty");

            await store.savePage();

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
                pageDetailsHandler(),
                http.put("/api/pages/{id}", ({ response }) => {
                    return response(200).json(updatedDetails);
                }),
            );
            const store = createHistoryEditorStore();
            await store.loadPageById(TEST_PAGE_ID);
            expect(store.isDirty).toBe(false);

            store.updateContent("updated content");
            expect(store.isDirty).toBe(true);

            await store.savePage();

            expect(store.currentPage).toEqual(updatedDetails);
            expect(store.isDirty).toBe(false);
        });

        it("keeps edits made during a save dirty", async () => {
            let releaseSave: () => void = () => {};
            const saveCanFinish = new Promise<void>((resolve) => {
                releaseSave = resolve;
            });
            const updatedDetails: HistoryPageDetails = {
                ...TEST_PAGE_DETAILS,
                content: "submitted content",
                update_time: "2025-06-16T09:00:00Z",
            };
            server.use(
                pageDetailsHandler(),
                http.put("/api/pages/{id}", async ({ response }) => {
                    await saveCanFinish;
                    return response(200).json(updatedDetails);
                }),
            );
            const store = createHistoryEditorStore();
            await store.loadPageById(TEST_PAGE_ID);
            store.updateContent("submitted content");

            const savePromise = store.savePage();
            store.updateContent("newer content");
            releaseSave();
            await savePromise;

            expect(store.currentContent).toBe("newer content");
            expect(store.isDirty).toBe(true);
        });

        it("sets isSaving during save", async () => {
            server.use(
                pageDetailsHandler(),
                http.put("/api/pages/{id}", ({ response }) => {
                    return response(200).json(TEST_PAGE_DETAILS);
                }),
            );
            const store = createHistoryEditorStore();
            await store.loadPageById(TEST_PAGE_ID);
            store.updateContent("new content");

            const promise = store.savePage();
            expect(store.isSaving).toBe(true);

            await promise;
            expect(store.isSaving).toBe(false);
        });

        it("sets error and rethrows on failure", async () => {
            server.use(
                pageDetailsHandler(),
                http.put("/api/pages/{id}", ({ response }) => {
                    return response("4XX").json({ err_msg: "Page is deleted", err_code: 400 }, { status: 400 });
                }),
            );
            const store = createHistoryEditorStore();
            await store.loadPageById(TEST_PAGE_ID);
            store.updateContent("new content");

            await expect(store.savePage()).rejects.toThrow();
            expect(store.error).toBeTruthy();
            expect(store.isSaving).toBe(false);
        });

        it("accepts empty content and clears dirty state", async () => {
            const updatedDetails: HistoryPageDetails = {
                ...TEST_PAGE_DETAILS,
                content: "",
                content_editor: "",
                update_time: "2025-06-16T10:00:00Z",
            };
            server.use(
                pageDetailsHandler(),
                http.put("/api/pages/{id}", ({ response }) => {
                    return response(200).json(updatedDetails);
                }),
            );
            const store = createHistoryEditorStore();
            await store.loadPageById(TEST_PAGE_ID);
            store.updateContent("");
            expect(store.isDirty).toBe(true);

            await store.savePage();

            expect(store.isDirty).toBe(false);
            expect(store.currentContent).toBe("");
            expect(store.error).toBeNull();
        });
    });

    describe("deleteCurrentPage", () => {
        it("does nothing if no currentPage", async () => {
            const store = createHistoryEditorStore();

            await store.deleteCurrentPage();

            expect(store.error).toBeNull();
        });

        it("does nothing if no historyId", async () => {
            const store = usePageEditorStore();
            store.currentPage = TEST_PAGE_DETAILS;

            await store.deleteCurrentPage();

            expect(store.currentPage).toEqual(TEST_PAGE_DETAILS);
        });

        it("clears current state and refreshes list on success", async () => {
            server.use(
                pageDetailsHandler(),
                pageListHandler(),
                http.delete("/api/pages/{id}", ({ response }) => {
                    return response(204).empty();
                }),
            );
            const store = createHistoryEditorStore();
            await store.loadPageById(TEST_PAGE_ID);
            expect(store.currentPage).not.toBeNull();

            server.use(pageListHandler([]));

            await store.deleteCurrentPage();

            expect(store.currentPage).toBeNull();
            expect(store.currentContent).toBe("");
            expect(store.currentTitle).toBe("");
            expect(store.isDirty).toBe(false);
            expect(store.pages).toEqual([]);
        });

        it("sets error and rethrows on failure", async () => {
            server.use(
                http.delete("/api/pages/{id}", ({ response }) => {
                    return response("4XX").json({ err_msg: "Page not found", err_code: 404 }, { status: 404 });
                }),
            );
            const store = createHistoryEditorStore();
            store.currentPage = TEST_PAGE_DETAILS;

            await expect(store.deleteCurrentPage()).rejects.toThrow();
            expect(store.error).toBeTruthy();
        });
    });

    describe("resolveCurrentPage", () => {
        it("returns stored ID when page still exists", async () => {
            server.use(pageListHandler());
            const store = usePageEditorStore();
            store.setCurrentPageId(TEST_HISTORY_ID, TEST_PAGE_ID);

            const result = await store.resolveCurrentPage(TEST_HISTORY_ID);
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
            server.use(pageListHandler([older, newer]));
            const store = usePageEditorStore();

            const result = await store.resolveCurrentPage(TEST_HISTORY_ID);
            expect(result).toBe("newer-page");
            expect(store.getCurrentPageId(TEST_HISTORY_ID)).toBe("newer-page");
        });

        it("creates page when history has none", async () => {
            const createdPage: HistoryPageDetails = {
                ...TEST_PAGE_DETAILS,
                id: "created-page",
            };
            server.use(
                pageListHandler([]),
                http.post("/api/pages", ({ response }) => {
                    return response(200).json(createdPage);
                }),
            );
            const store = usePageEditorStore();

            const result = await store.resolveCurrentPage(TEST_HISTORY_ID);
            expect(result).toBe("created-page");
            expect(store.getCurrentPageId(TEST_HISTORY_ID)).toBe("created-page");
        });

        it("re-resolves on stale mapping (deleted page)", async () => {
            const freshPage: HistoryPageSummary = {
                ...TEST_PAGE_SUMMARY,
                id: "fresh-page",
            };
            server.use(pageListHandler([freshPage]));
            const store = usePageEditorStore();
            store.setCurrentPageId(TEST_HISTORY_ID, "deleted-page");

            const result = await store.resolveCurrentPage(TEST_HISTORY_ID);
            expect(result).toBe("fresh-page");
            expect(store.getCurrentPageId(TEST_HISTORY_ID)).toBe("fresh-page");
        });
    });

    describe("currentPageId tracking", () => {
        it("loadPageById updates stored current ID", async () => {
            server.use(pageDetailsHandler());
            const store = createHistoryEditorStore();

            await store.loadPageById(TEST_PAGE_ID);

            expect(store.getCurrentPageId(TEST_HISTORY_ID)).toBe(TEST_PAGE_ID);
        });

        it("deleteCurrentPage clears stored ID", async () => {
            server.use(
                pageDetailsHandler(),
                pageListHandler([]),
                http.delete("/api/pages/{id}", ({ response }) => {
                    return response(204).empty();
                }),
            );
            const store = createHistoryEditorStore();
            await store.loadPageById(TEST_PAGE_ID);
            expect(store.getCurrentPageId(TEST_HISTORY_ID)).toBe(TEST_PAGE_ID);

            await store.deleteCurrentPage();

            expect(store.getCurrentPageId(TEST_HISTORY_ID)).toBeNull();
        });

        it("remembers page IDs per history and clears only the requested history", () => {
            const store = usePageEditorStore();

            store.setCurrentPageId("h1", "p1");
            store.setCurrentPageId("h2", "p2");

            expect(store.getCurrentPageId("h1")).toBe("p1");
            expect(store.getCurrentPageId("h2")).toBe("p2");
            expect(store.getCurrentPageId("h3")).toBeNull();

            store.clearCurrentPageId("h1");
            expect(store.getCurrentPageId("h1")).toBeNull();
            expect(store.getCurrentPageId("h2")).toBe("p2");
        });
    });

    describe("editing and resetting page state", () => {
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
            server.use(pageDetailsHandler(pageWithContent));
            const store = createHistoryEditorStore();
            await store.loadPageById(TEST_PAGE_ID);
            expect(store.currentContent).toBe("original content");

            store.updateContent("modified");
            expect(store.isDirty).toBe(true);

            store.discardChanges();

            expect(store.currentContent).toBe("original content");
            expect(store.isDirty).toBe(false);
        });

        it("clearCurrentPage resets current page state", async () => {
            server.use(pageDetailsHandler());
            const store = createHistoryEditorStore();
            await store.loadPageById(TEST_PAGE_ID);
            store.updateContent("modified");
            expect(store.currentPage).not.toBeNull();
            expect(store.isDirty).toBe(true);

            store.clearCurrentPage();

            expect(store.currentPage).toBeNull();
            expect(store.currentContent).toBe("");
            expect(store.currentTitle).toBe("");
            expect(store.isDirty).toBe(false);
        });

        it("clearCurrentPage does not affect pages list or historyId", () => {
            const store = createHistoryEditorStore();
            store.pages = [TEST_PAGE_SUMMARY];
            store.currentPage = TEST_PAGE_DETAILS;

            store.clearCurrentPage();

            expect(store.historyId).toBe(TEST_HISTORY_ID);
            expect(store.pages).toEqual([TEST_PAGE_SUMMARY]);
        });

        it("$reset resets all state including mode", async () => {
            server.use(pageListHandler(), pageDetailsHandler());
            const store = usePageEditorStore();
            store.mode = "standalone";
            await store.loadPages(TEST_HISTORY_ID);
            await store.loadPageById(TEST_PAGE_ID);
            store.updateContent("modified");
            store.updateTitle("new title");
            store.$patch({
                isSaving: true,
                error: "some error",
            });

            store.$reset();

            expect(store.mode).toBe("history");
            expect(store.pages).toEqual([]);
            expect(store.currentPage).toBeNull();
            expect(store.currentContent).toBe("");
            expect(store.currentTitle).toBe("");
            expect(store.isDirty).toBe(false);
            expect(store.isLoadingList).toBe(false);
            expect(store.isLoadingPage).toBe(false);
            expect(store.isSaving).toBe(false);
            expect(store.error).toBeNull();
            expect(store.historyId).toBeNull();
        });
    });

    describe("revisionViewMode", () => {
        it("defaults to 'preview'", () => {
            const store = usePageEditorStore();
            expect(store.revisionViewMode).toBe("preview");
        });

        it("clearSelectedRevision resets to 'preview'", () => {
            const store = usePageEditorStore();
            store.revisionViewMode = "changes_current";

            store.clearSelectedRevision();

            expect(store.revisionViewMode).toBe("preview");
        });

        it("clearing the page returns the revision view to preview", () => {
            const store = usePageEditorStore();
            store.revisionViewMode = "changes_current";

            store.showRevisions = true;

            store.clearCurrentPage();

            expect(store.revisionViewMode).toBe("preview");
        });

        it("$reset resets to 'preview'", () => {
            const store = usePageEditorStore();
            store.revisionViewMode = "changes_current";

            store.$reset();

            expect(store.revisionViewMode).toBe("preview");
        });
    });

    describe("revision navigation boundaries", () => {
        it("marks the first revision in newest-first order as newest", () => {
            const store = usePageEditorStore();
            store.$patch({
                revisions: [
                    createRevisionSummary({ id: "rev-2", create_time: "2025-01-02", update_time: "2025-01-02" }),
                    createRevisionSummary(),
                ],
            });
            store.selectedRevision = createRevisionDetails({
                id: "rev-2",
                create_time: "2025-01-02",
                update_time: "2025-01-02",
            });
            expect(store.isNewestRevision).toBe(true);
            expect(store.isOldestRevision).toBe(false);
        });

        it("marks the last revision in newest-first order as oldest", () => {
            const store = usePageEditorStore();
            store.$patch({
                revisions: [
                    createRevisionSummary({ id: "rev-2", create_time: "2025-01-02", update_time: "2025-01-02" }),
                    createRevisionSummary(),
                ],
            });
            store.selectedRevision = createRevisionDetails();
            expect(store.isNewestRevision).toBe(false);
            expect(store.isOldestRevision).toBe(true);
        });

        it("marks a middle revision as neither newest nor oldest", () => {
            const store = usePageEditorStore();
            store.$patch({
                revisions: [
                    createRevisionSummary({ id: "rev-3", create_time: "2025-01-03", update_time: "2025-01-03" }),
                    createRevisionSummary({ id: "rev-2", create_time: "2025-01-02", update_time: "2025-01-02" }),
                    createRevisionSummary(),
                ],
            });
            store.selectedRevision = createRevisionDetails({
                id: "rev-2",
                create_time: "2025-01-02",
                update_time: "2025-01-02",
            });
            expect(store.isNewestRevision).toBe(false);
            expect(store.isOldestRevision).toBe(false);
        });

        it("marks neither boundary when no revision is selected", () => {
            const store = usePageEditorStore();
            expect(store.isNewestRevision).toBe(false);
            expect(store.isOldestRevision).toBe(false);
        });
    });

    describe("previousRevisionContent", () => {
        it("is set after loadRevision when predecessor exists", async () => {
            const revSummaries = [
                createRevisionSummary({ id: "rev-2", create_time: "2025-01-02", update_time: "2025-01-02" }),
                createRevisionSummary(),
            ];
            const rev2Details = createRevisionDetails({
                ...revSummaries[0],
                content: "# V2",
                content_editor: "# V2",
                title: "",
            });
            const rev1Details = createRevisionDetails({
                ...revSummaries[1],
                content: "# V1",
                content_editor: "# V1",
                title: "",
            });
            server.use(
                http.get("/api/pages/{id}/revisions/{revision_id}", ({ params, response }) => {
                    if (params["revision_id"] === "rev-2") {
                        return response(200).json(rev2Details);
                    }
                    return response(200).json(rev1Details);
                }),
            );
            const store = usePageEditorStore();
            store.currentPage = TEST_PAGE_DETAILS;
            store.revisions = revSummaries;

            await store.loadRevision("rev-2");

            expect(store.selectedRevision?.id).toBe("rev-2");
            expect(store.previousRevisionContent).toBe("# V1");
        });

        it("is null when selected is the oldest (no predecessor)", async () => {
            const revSummaries = [createRevisionSummary()];
            const rev1Details = createRevisionDetails({
                ...revSummaries[0],
                content: "# V1",
                content_editor: "# V1",
                title: "",
            });
            server.use(
                http.get("/api/pages/{id}/revisions/{revision_id}", ({ response }) => {
                    return response(200).json(rev1Details);
                }),
            );
            const store = usePageEditorStore();
            store.currentPage = TEST_PAGE_DETAILS;
            store.revisions = revSummaries;

            await store.loadRevision("rev-1");

            expect(store.previousRevisionContent).toBeNull();
        });

        it("is cleared by clearSelectedRevision", () => {
            const store = usePageEditorStore();
            store.previousRevisionContent = "old";
            store.clearSelectedRevision();
            expect(store.previousRevisionContent).toBeNull();
        });

        it("is cleared when the current page is cleared", () => {
            const store = usePageEditorStore();
            store.previousRevisionContent = "old";
            store.clearCurrentPage();
            expect(store.previousRevisionContent).toBeNull();
        });
    });

    describe("standalone mode", () => {
        const STANDALONE_PAGE: HistoryPageDetails = {
            ...TEST_PAGE_DETAILS,
            history_id: null,
        };

        it("loadPage loads a standalone page without historyId", async () => {
            server.use(pageDetailsHandler(STANDALONE_PAGE));
            const store = usePageEditorStore();
            store.mode = "standalone";

            await store.loadPage(TEST_PAGE_ID);

            expect(store.currentPage).toEqual(STANDALONE_PAGE);
            expect(store.currentContent).toBe(STANDALONE_PAGE.content_editor);
            expect(store.historyId).toBeNull();
        });

        it("savePage in standalone mode defaults edit_source to user", async () => {
            let capturedBody: UpdateHistoryPagePayload | undefined;
            server.use(
                http.put("/api/pages/{id}", async ({ request, response }) => {
                    capturedBody = await request.json();
                    return response(200).json(STANDALONE_PAGE);
                }),
            );
            const store = usePageEditorStore();
            store.mode = "standalone";
            store.currentPage = STANDALONE_PAGE;
            store.updateContent("new content");

            await store.savePage();

            expect(capturedBody?.edit_source).toBe("user");
        });

        it("loadRevisions works without historyId", async () => {
            const revisions = [
                createRevisionSummary(),
                createRevisionSummary({ id: "rev-2", create_time: "2025-01-02", update_time: "2025-01-02" }),
            ];
            server.use(
                http.get("/api/pages/{id}/revisions", ({ response }) => {
                    return response(200).json(revisions);
                }),
            );
            const store = usePageEditorStore();
            store.mode = "standalone";
            store.currentPage = STANDALONE_PAGE;

            await store.loadRevisions();

            expect(store.revisions).toHaveLength(2);
            expect(store.revisions[0]!.id).toBe("rev-1");
        });

        it("restoreRevision works without historyId", async () => {
            const restoredRevision = createRevisionDetails({
                id: "rev-new",
                edit_source: "restore",
                create_time: "2025-01-03",
                update_time: "2025-01-03",
            });
            server.use(
                http.post("/api/pages/{id}/revisions/{revision_id}/revert", ({ response }) => {
                    return response(200).json(restoredRevision);
                }),
                pageDetailsHandler(STANDALONE_PAGE),
                http.get("/api/pages/{id}/revisions", ({ response }) => {
                    return response(200).json([restoredRevision]);
                }),
            );
            const store = usePageEditorStore();
            store.mode = "standalone";
            store.currentPage = STANDALONE_PAGE;

            await store.restoreRevision("rev-1");

            expect(store.selectedRevision).toBeNull();
            expect(store.showRevisions).toBe(false);
        });
    });

    describe("chatError", () => {
        it("is null by default", () => {
            const store = usePageEditorStore();
            expect(store.chatError).toBeNull();
        });

        it("is reset to null on clearCurrentPage", () => {
            const store = usePageEditorStore();
            store.chatError = "some error";
            store.clearCurrentPage();
            expect(store.chatError).toBeNull();
        });

        it("is reset to null on $reset", () => {
            const store = usePageEditorStore();
            store.chatError = "some error";
            store.$reset();
            expect(store.chatError).toBeNull();
        });
    });

    describe("chat exchange IDs", () => {
        it("returns null for an unknown page", () => {
            const store = usePageEditorStore();
            expect(store.getCurrentChatExchangeId("page-1")).toBeNull();
        });

        it("stores and retrieves an exchange ID per page", () => {
            const store = usePageEditorStore();
            store.setCurrentChatExchangeId("page-1", "exchange-abc");
            expect(store.getCurrentChatExchangeId("page-1")).toBe("exchange-abc");
        });

        it("isolates IDs across different pages", () => {
            const store = usePageEditorStore();
            store.setCurrentChatExchangeId("page-1", "ex-1");
            store.setCurrentChatExchangeId("page-2", "ex-2");
            expect(store.getCurrentChatExchangeId("page-1")).toBe("ex-1");
            expect(store.getCurrentChatExchangeId("page-2")).toBe("ex-2");
        });

        it("clears a specific page ID without affecting others", () => {
            const store = usePageEditorStore();
            store.setCurrentChatExchangeId("page-1", "ex-1");
            store.setCurrentChatExchangeId("page-2", "ex-2");
            store.clearCurrentChatExchangeId("page-1");
            expect(store.getCurrentChatExchangeId("page-1")).toBeNull();
            expect(store.getCurrentChatExchangeId("page-2")).toBe("ex-2");
        });

        it("overrides an existing entry when set again", () => {
            const store = usePageEditorStore();
            store.setCurrentChatExchangeId("page-1", "ex-1");
            store.setCurrentChatExchangeId("page-1", "ex-2");
            expect(store.getCurrentChatExchangeId("page-1")).toBe("ex-2");
        });
    });
});
