/**
 * Tests for the historyPages API client (replaces old historyNotebooks tests).
 * The historyPages module uses plain axios, but MSW intercepts all HTTP.
 */
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import type { HistoryPageDetails, HistoryPageSummary } from "./historyPages";
import {
    createHistoryPage,
    deleteHistoryPage,
    fetchHistoryPage,
    fetchHistoryPages,
    updateHistoryPage,
} from "./historyPages";

const { server, http } = useServerMock();

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

describe("historyPages API", () => {
    describe("fetchHistoryPages", () => {
        it("returns list of pages for a history", async () => {
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response(200).json([TEST_PAGE_SUMMARY]);
                }) as any,
            );

            const result = await fetchHistoryPages(TEST_HISTORY_ID);

            expect(result).toEqual([TEST_PAGE_SUMMARY]);
        });

        it("returns empty list when history has no pages", async () => {
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response(200).json([]);
                }) as any,
            );

            const result = await fetchHistoryPages(TEST_HISTORY_ID);

            expect(result).toEqual([]);
        });

        it("throws on server error", async () => {
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "History not found", err_code: 404 }, { status: 404 });
                }) as any,
            );

            await expect(fetchHistoryPages(TEST_HISTORY_ID)).rejects.toThrow();
        });
    });

    describe("fetchHistoryPage", () => {
        it("returns page details by id", async () => {
            server.use(
                http.get("/api/pages/:id", ({ response }) => {
                    return response(200).json(TEST_PAGE_DETAILS);
                }) as any,
            );

            const result = await fetchHistoryPage(TEST_PAGE_ID);

            expect(result).toEqual(TEST_PAGE_DETAILS);
        });

        it("throws on page not found", async () => {
            server.use(
                http.get("/api/pages/:id", ({ response }) => {
                    return response("4XX").json({ err_msg: "Page not found", err_code: 404 }, { status: 404 });
                }) as any,
            );

            await expect(fetchHistoryPage("nonexistent")).rejects.toThrow();
        });
    });

    describe("createHistoryPage", () => {
        const CREATE_PAYLOAD = {
            content: "# New Page\n\nInitial content.",
            content_format: "markdown",
            title: "New Page",
            history_id: TEST_HISTORY_ID,
        };

        it("returns created page details", async () => {
            server.use(
                http.post("/api/pages", ({ response }) => {
                    return response(200).json({
                        ...TEST_PAGE_DETAILS,
                        title: "New Page",
                        content: "# New Page\n\nInitial content.",
                    });
                }) as any,
            );

            const result = await createHistoryPage(CREATE_PAYLOAD);

            expect(result.title).toBe("New Page");
            expect(result.content).toBe("# New Page\n\nInitial content.");
            expect(result.history_id).toBe(TEST_HISTORY_ID);
            expect(result.id).toBe(TEST_PAGE_ID);
        });

        it("throws on creation error", async () => {
            server.use(
                http.post("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "Cannot create page", err_code: 400 }, { status: 400 });
                }) as any,
            );

            await expect(createHistoryPage(CREATE_PAYLOAD)).rejects.toThrow();
        });
    });

    describe("updateHistoryPage", () => {
        const UPDATE_PAYLOAD = {
            content: "# Updated Content\n\nRevised analysis.",
            content_format: "markdown",
            title: "Updated Title",
        };

        it("returns updated page details", async () => {
            server.use(
                http.put("/api/pages/:id", ({ response }) => {
                    return response(200).json({
                        ...TEST_PAGE_DETAILS,
                        title: "Updated Title",
                        content: "# Updated Content\n\nRevised analysis.",
                        update_time: "2025-06-16T09:00:00Z",
                    });
                }) as any,
            );

            const result = await updateHistoryPage(TEST_PAGE_ID, UPDATE_PAYLOAD);

            expect(result.title).toBe("Updated Title");
            expect(result.content).toBe("# Updated Content\n\nRevised analysis.");
            expect(result.update_time).toBe("2025-06-16T09:00:00Z");
        });

        it("throws on update error", async () => {
            server.use(
                http.put("/api/pages/:id", ({ response }) => {
                    return response("4XX").json({ err_msg: "Page is deleted", err_code: 400 }, { status: 400 });
                }) as any,
            );

            await expect(updateHistoryPage(TEST_PAGE_ID, UPDATE_PAYLOAD)).rejects.toThrow();
        });
    });

    describe("deleteHistoryPage", () => {
        it("resolves without error on success", async () => {
            server.use(
                http.delete("/api/pages/:id", ({ response }) => {
                    return response(204).empty();
                }) as any,
            );

            await expect(deleteHistoryPage(TEST_PAGE_ID)).resolves.toBeUndefined();
        });

        it("throws on deletion error", async () => {
            server.use(
                http.delete("/api/pages/:id", ({ response }) => {
                    return response("4XX").json({ err_msg: "Page not found", err_code: 404 }, { status: 404 });
                }) as any,
            );

            await expect(deleteHistoryPage(TEST_PAGE_ID)).rejects.toThrow();
        });
    });
});
