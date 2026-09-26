/**
 * Tests for the unified pages API client.
 */
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import type {
    CreateHistoryPagePayload,
    HistoryPageDetails,
    HistoryPageSummary,
    UpdateHistoryPagePayload,
} from "./pages";
import {
    createHistoryPage,
    createPage,
    deleteHistoryPage,
    fetchHistoryPage,
    fetchHistoryPages,
    loadPages,
    savePage,
    updateHistoryPage,
} from "./pages";

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

describe("pages API", () => {
    describe("fetchHistoryPages", () => {
        it("returns list of pages for a history", async () => {
            server.use(
                http.get("/api/pages", ({ response }: any) => {
                    return response(200).json([TEST_PAGE_SUMMARY]);
                }) as any,
            );

            const result = await fetchHistoryPages(TEST_HISTORY_ID);

            expect(result).toEqual([TEST_PAGE_SUMMARY]);
        });

        it("returns empty list when history has no pages", async () => {
            server.use(
                http.get("/api/pages", ({ response }: any) => {
                    return response(200).json([]);
                }) as any,
            );

            const result = await fetchHistoryPages(TEST_HISTORY_ID);

            expect(result).toEqual([]);
        });

        it("throws on server error", async () => {
            server.use(
                http.get("/api/pages", ({ response }: any) => {
                    return response("4XX").json({ err_msg: "History not found", err_code: 404 }, { status: 404 });
                }) as any,
            );

            await expect(fetchHistoryPages(TEST_HISTORY_ID)).rejects.toThrow();
        });
    });

    describe("fetchHistoryPage", () => {
        it("returns page details by id", async () => {
            server.use(
                http.get("/api/pages/{id}", ({ response }: any) => {
                    return response(200).json(TEST_PAGE_DETAILS);
                }) as any,
            );

            const result = await fetchHistoryPage(TEST_PAGE_ID);

            expect(result).toEqual(TEST_PAGE_DETAILS);
        });

        it("throws on page not found", async () => {
            server.use(
                http.get("/api/pages/{id}", ({ response }: any) => {
                    return response("4XX").json({ err_msg: "Page not found", err_code: 404 }, { status: 404 });
                }) as any,
            );

            await expect(fetchHistoryPage("nonexistent")).rejects.toThrow();
        });
    });

    describe("createHistoryPage", () => {
        const CREATE_PAYLOAD: CreateHistoryPagePayload = {
            content: "# New Page\n\nInitial content.",
            content_format: "markdown",
            title: "New Page",
            history_id: TEST_HISTORY_ID,
        };

        it("returns created page details", async () => {
            server.use(
                http.post("/api/pages", ({ response }: any) => {
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
                http.post("/api/pages", ({ response }: any) => {
                    return response("4XX").json({ err_msg: "Cannot create page", err_code: 400 }, { status: 400 });
                }) as any,
            );

            await expect(createHistoryPage(CREATE_PAYLOAD)).rejects.toThrow();
        });
    });

    describe("updateHistoryPage", () => {
        const UPDATE_PAYLOAD: UpdateHistoryPagePayload = {
            content: "# Updated Content\n\nRevised analysis.",
            content_format: "markdown",
            title: "Updated Title",
        };

        it("returns updated page details", async () => {
            server.use(
                http.put("/api/pages/{id}", ({ response }: any) => {
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
                http.put("/api/pages/{id}", ({ response }: any) => {
                    return response("4XX").json({ err_msg: "Page is deleted", err_code: 400 }, { status: 400 });
                }) as any,
            );

            await expect(updateHistoryPage(TEST_PAGE_ID, UPDATE_PAYLOAD)).rejects.toThrow();
        });
    });

    describe("savePage", () => {
        it("saves content via PUT with default edit_source", async () => {
            server.use(
                http.put("/api/pages/{id}", ({ response }: any) => {
                    return response(200).json({
                        ...TEST_PAGE_DETAILS,
                        content: "# Saved Content",
                        edit_source: "user",
                    });
                }) as any,
            );

            const result = await savePage(TEST_PAGE_ID, "# Saved Content");

            expect(result.content).toBe("# Saved Content");
            expect(result.edit_source).toBe("user");
        });

        it("saves content with custom edit_source", async () => {
            server.use(
                http.put("/api/pages/{id}", ({ response }: any) => {
                    return response(200).json({
                        ...TEST_PAGE_DETAILS,
                        content: "# Agent Content",
                        edit_source: "agent",
                    });
                }) as any,
            );

            const result = await savePage(TEST_PAGE_ID, "# Agent Content", "agent");

            expect(result.content).toBe("# Agent Content");
            expect(result.edit_source).toBe("agent");
        });
    });

    describe("loadPages", () => {
        it("requests own pages and parses total matches by default", async () => {
            let query: URLSearchParams | undefined;

            server.use(
                http.get("/api/pages", ({ request, response }) => {
                    query = new URL(request.url).searchParams;
                    return response(200).json([TEST_PAGE_SUMMARY], { headers: { total_matches: "7" } });
                }),
            );

            const result = await loadPages();

            expect(result.data).toEqual([TEST_PAGE_SUMMARY]);
            expect(result.totalMatches).toBe(7);
            expect(query?.get("show_own")).toBe("true");
            expect(query?.get("show_shared")).toBe("false");
            expect(query?.get("show_published")).toBe("false");
            expect(query?.get("sort_by")).toBe("update_time");
            expect(query?.get("sort_desc")).toBe("true");
            expect(query?.get("limit")).toBe("20");
            expect(query?.get("offset")).toBe("0");
        });

        it("passes through visibility, search, sorting and paging options", async () => {
            let query: URLSearchParams | undefined;

            server.use(
                http.get("/api/pages", ({ request, response }) => {
                    query = new URL(request.url).searchParams;
                    return response(200).json([]);
                }),
            );

            await loadPages({
                showOwn: false,
                showShared: true,
                showPublished: true,
                search: "analysis",
                sortBy: "title",
                sortDesc: false,
                limit: 5,
                offset: 10,
            });

            expect(query?.get("show_own")).toBe("false");
            expect(query?.get("show_shared")).toBe("true");
            expect(query?.get("show_published")).toBe("true");
            expect(query?.get("search")).toBe("analysis");
            expect(query?.get("sort_by")).toBe("title");
            expect(query?.get("sort_desc")).toBe("false");
            expect(query?.get("limit")).toBe("5");
            expect(query?.get("offset")).toBe("10");
        });

        it("converts the is:standalone filter to the backend type filter", async () => {
            let query: URLSearchParams | undefined;

            server.use(
                http.get("/api/pages", ({ request, response }) => {
                    query = new URL(request.url).searchParams;
                    return response(200).json([]);
                }),
            );

            await loadPages({ search: "notes is:standalone" });

            expect(query?.get("search")).toBe("notes type:standalone");
        });

        it("defaults total matches to zero when the header is missing", async () => {
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response(200).json([]);
                }),
            );

            const result = await loadPages();

            expect(result.totalMatches).toBe(0);
        });

        it("throws on server error", async () => {
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "Not allowed", err_code: 403 }, { status: 403 });
                }),
            );

            await expect(loadPages()).rejects.toThrow();
        });
    });

    describe("createPage", () => {
        it("creates a markdown page by default and returns it", async () => {
            let body: Record<string, unknown> | undefined;

            server.use(
                http.post("/api/pages", async ({ request, response }) => {
                    body = (await request.json()) as Record<string, unknown>;
                    return response(200).json({ ...TEST_PAGE_DETAILS, title: "My Notes", slug: "my-notes" });
                }),
            );

            const result = await createPage({ title: "My Notes", slug: "my-notes" });

            expect(body).toEqual({
                title: "My Notes",
                slug: "my-notes",
                content: "",
                content_format: "markdown",
            });
            expect(result.id).toBe(TEST_PAGE_ID);
            expect(result.slug).toBe("my-notes");
        });

        it("allows overriding the content format and content", async () => {
            let body: Record<string, unknown> | undefined;

            server.use(
                http.post("/api/pages", async ({ request, response }) => {
                    body = (await request.json()) as Record<string, unknown>;
                    return response(200).json(TEST_PAGE_DETAILS);
                }),
            );

            await createPage({ title: "Legacy", slug: "legacy", content_format: "html", content: "<p>hi</p>" });

            expect(body).toEqual({
                title: "Legacy",
                slug: "legacy",
                content: "<p>hi</p>",
                content_format: "html",
            });
        });

        it("throws when the slug is already taken", async () => {
            server.use(
                http.post("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "Slug already exists", err_code: 400 }, { status: 400 });
                }),
            );

            await expect(createPage({ title: "My Notes", slug: "my-notes" })).rejects.toThrow();
        });
    });

    describe("deleteHistoryPage", () => {
        it("resolves without error on success", async () => {
            server.use(
                http.delete("/api/pages/{id}", ({ response }: any) => {
                    return response(204).empty();
                }) as any,
            );

            await expect(deleteHistoryPage(TEST_PAGE_ID)).resolves.toBeUndefined();
        });

        it("throws on deletion error", async () => {
            server.use(
                http.delete("/api/pages/{id}", ({ response }: any) => {
                    return response("4XX").json({ err_msg: "Page not found", err_code: 404 }, { status: 404 });
                }) as any,
            );

            await expect(deleteHistoryPage(TEST_PAGE_ID)).rejects.toThrow();
        });
    });
});
