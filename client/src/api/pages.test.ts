/**
 * Tests for the unified pages API client.
 */
import { getFakePageDetails, getFakePageSummary } from "@tests/test-data/pages";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import type { CreateHistoryPagePayload, UpdateHistoryPagePayload } from "./pages";
import {
    createHistoryPage,
    createPage,
    createPageFromTitle,
    deleteHistoryPage,
    fetchHistoryPage,
    fetchHistoryPages,
    loadPages,
    PageSlugConflictError,
    savePage,
    updateHistoryPage,
} from "./pages";

const { server, http } = useServerMock();

const TEST_HISTORY_ID = "abc123historyid";
const TEST_PAGE_ID = "def456pageid";
const TEST_PAGE_SUMMARY = getFakePageSummary();
const TEST_PAGE_DETAILS = getFakePageDetails();

describe("pages API", () => {
    describe("fetchHistoryPages", () => {
        it("returns list of pages for a history", async () => {
            let historyId: string | null = null;
            server.use(
                http.get("/api/pages", ({ request, response }) => {
                    historyId = new URL(request.url).searchParams.get("history_id");
                    return response(200).json([TEST_PAGE_SUMMARY]);
                }),
            );

            const result = await fetchHistoryPages(TEST_HISTORY_ID);

            expect(historyId).toBe(TEST_HISTORY_ID);
            expect(result).toEqual([TEST_PAGE_SUMMARY]);
        });

        it("returns empty list when history has no pages", async () => {
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response(200).json([]);
                }),
            );

            const result = await fetchHistoryPages(TEST_HISTORY_ID);

            expect(result).toEqual([]);
        });

        it("throws on server error", async () => {
            server.use(
                http.get("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "History not found", err_code: 404 }, { status: 404 });
                }),
            );

            await expect(fetchHistoryPages(TEST_HISTORY_ID)).rejects.toThrow();
        });
    });

    describe("fetchHistoryPage", () => {
        it("returns page details by id", async () => {
            let requestedPageId: string | undefined;
            server.use(
                http.get("/api/pages/{id}", ({ params, response }) => {
                    requestedPageId = params.id;
                    return response(200).json(TEST_PAGE_DETAILS);
                }),
            );

            const result = await fetchHistoryPage(TEST_PAGE_ID);

            expect(requestedPageId).toBe(TEST_PAGE_ID);
            expect(result).toEqual(TEST_PAGE_DETAILS);
        });

        it("throws on page not found", async () => {
            server.use(
                http.get("/api/pages/{id}", ({ response }) => {
                    return response("4XX").json({ err_msg: "Page not found", err_code: 404 }, { status: 404 });
                }),
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
            let body: CreateHistoryPagePayload | undefined;
            server.use(
                http.post("/api/pages", async ({ request, response }) => {
                    body = await request.json();
                    return response(200).json({
                        ...TEST_PAGE_DETAILS,
                        title: "New Page",
                        content: "# New Page\n\nInitial content.",
                    });
                }),
            );

            const result = await createHistoryPage(CREATE_PAYLOAD);

            expect(body).toEqual(CREATE_PAYLOAD);
            expect(result.title).toBe("New Page");
            expect(result.content).toBe("# New Page\n\nInitial content.");
            expect(result.history_id).toBe(TEST_HISTORY_ID);
            expect(result.id).toBe(TEST_PAGE_ID);
        });

        it("throws on creation error", async () => {
            server.use(
                http.post("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "Cannot create page", err_code: 400 }, { status: 400 });
                }),
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
            let body: UpdateHistoryPagePayload | undefined;
            let requestedPageId: string | undefined;
            server.use(
                http.put("/api/pages/{id}", async ({ params, request, response }) => {
                    requestedPageId = params.id;
                    body = await request.json();
                    return response(200).json({
                        ...TEST_PAGE_DETAILS,
                        title: "Updated Title",
                        content: "# Updated Content\n\nRevised analysis.",
                        update_time: "2025-06-16T09:00:00Z",
                    });
                }),
            );

            const result = await updateHistoryPage(TEST_PAGE_ID, UPDATE_PAYLOAD);

            expect(requestedPageId).toBe(TEST_PAGE_ID);
            expect(body).toEqual(UPDATE_PAYLOAD);
            expect(result.title).toBe("Updated Title");
            expect(result.content).toBe("# Updated Content\n\nRevised analysis.");
            expect(result.update_time).toBe("2025-06-16T09:00:00Z");
        });

        it("throws on update error", async () => {
            server.use(
                http.put("/api/pages/{id}", ({ response }) => {
                    return response("4XX").json({ err_msg: "Page is deleted", err_code: 400 }, { status: 400 });
                }),
            );

            await expect(updateHistoryPage(TEST_PAGE_ID, UPDATE_PAYLOAD)).rejects.toThrow();
        });
    });

    describe("savePage", () => {
        it("saves content via PUT with default edit_source", async () => {
            let body: UpdateHistoryPagePayload | undefined;
            let requestedPageId: string | undefined;
            server.use(
                http.put("/api/pages/{id}", async ({ params, request, response }) => {
                    requestedPageId = params.id;
                    body = await request.json();
                    return response(200).json({
                        ...TEST_PAGE_DETAILS,
                        content: "# Saved Content",
                        edit_source: "user",
                    });
                }),
            );

            const result = await savePage(TEST_PAGE_ID, "# Saved Content");

            expect(requestedPageId).toBe(TEST_PAGE_ID);
            expect(body).toEqual({ content: "# Saved Content", edit_source: "user" });
            expect(result.content).toBe("# Saved Content");
            expect(result.edit_source).toBe("user");
        });

        it("saves content with custom edit_source", async () => {
            let body: UpdateHistoryPagePayload | undefined;
            let requestedPageId: string | undefined;
            server.use(
                http.put("/api/pages/{id}", async ({ params, request, response }) => {
                    requestedPageId = params.id;
                    body = await request.json();
                    return response(200).json({
                        ...TEST_PAGE_DETAILS,
                        content: "# Agent Content",
                        edit_source: "agent",
                    });
                }),
            );

            const result = await savePage(TEST_PAGE_ID, "# Agent Content", "agent");

            expect(requestedPageId).toBe(TEST_PAGE_ID);
            expect(body).toEqual({ content: "# Agent Content", edit_source: "agent" });
            expect(result.content).toBe("# Agent Content");
            expect(result.edit_source).toBe("agent");
        });
    });

    describe("loadPages", () => {
        it("requests own pages and parses total matches by default", async () => {
            let query: Record<string, string> | undefined;

            server.use(
                http.get("/api/pages", ({ request, response }) => {
                    query = Object.fromEntries(new URL(request.url).searchParams);
                    return response(200).json([TEST_PAGE_SUMMARY], { headers: { total_matches: "7" } });
                }),
            );

            const result = await loadPages();

            expect(result.data).toEqual([TEST_PAGE_SUMMARY]);
            expect(result.totalMatches).toBe(7);
            expect(query).toMatchObject({
                show_own: "true",
                show_shared: "false",
                show_published: "false",
                sort_by: "update_time",
                sort_desc: "true",
                limit: "20",
                offset: "0",
            });
        });

        it("passes through visibility, search, sorting and paging options", async () => {
            let query: Record<string, string> | undefined;

            server.use(
                http.get("/api/pages", ({ request, response }) => {
                    query = Object.fromEntries(new URL(request.url).searchParams);
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

            expect(query).toMatchObject({
                show_own: "false",
                show_shared: "true",
                show_published: "true",
                search: "analysis",
                sort_by: "title",
                sort_desc: "false",
                limit: "5",
                offset: "10",
            });
        });

        it("converts the is:standalone filter to the backend type filter", async () => {
            let query: Record<string, string> | undefined;

            server.use(
                http.get("/api/pages", ({ request, response }) => {
                    query = Object.fromEntries(new URL(request.url).searchParams);
                    return response(200).json([]);
                }),
            );

            await loadPages({ search: "notes is:standalone" });

            expect(query?.search).toBe("notes type:standalone");
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
            let body: CreateHistoryPagePayload | undefined;

            server.use(
                http.post("/api/pages", async ({ request, response }) => {
                    body = await request.json();
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
            let body: CreateHistoryPagePayload | undefined;

            server.use(
                http.post("/api/pages", async ({ request, response }) => {
                    body = await request.json();
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

        it("throws a slug conflict on the backend's duplicate slug code alone", async () => {
            server.use(
                http.post("/api/pages", ({ response }) => {
                    return response("4XX").json(
                        { err_msg: "Page identifier must be unique", err_code: 400006 },
                        { status: 400 },
                    );
                }),
            );

            await expect(createPage({ title: "My Notes", slug: "my-notes" })).rejects.toBeInstanceOf(
                PageSlugConflictError,
            );
        });

        it("throws a plain error for any other failure", async () => {
            server.use(
                http.post("/api/pages", ({ response }) => {
                    return response("4XX").json({ err_msg: "Slug already exists", err_code: 400 }, { status: 400 });
                }),
            );

            const created = createPage({ title: "My Notes", slug: "my-notes" });

            await expect(created).rejects.toThrow("Slug already exists");
            await expect(created).rejects.not.toBeInstanceOf(PageSlugConflictError);
        });
    });

    describe("createPageFromTitle", () => {
        function mockPageCreation(...outcomes: ("created" | "slug-conflict")[]) {
            const slugs: unknown[] = [];
            server.use(
                http.post("/api/pages", async ({ request, response }) => {
                    const body = await request.json();
                    slugs.push(body.slug);
                    if (outcomes[slugs.length - 1] === "slug-conflict") {
                        return response("4XX").json(
                            { err_msg: "Page identifier must be unique", err_code: 400006 },
                            { status: 400 },
                        );
                    }
                    return response(200).json({ ...TEST_PAGE_DETAILS, slug: body.slug });
                }),
            );
            return slugs;
        }

        it.each([
            { name: "slugs a title with words", title: "My New Page", expectedSlug: "my-new-page" },
            { name: "uses a fallback for a title without usable characters", title: "!!!", expectedSlug: "page" },
        ])("$name", async ({ title, expectedSlug }) => {
            const slugs = mockPageCreation("created");

            await createPageFromTitle({ title });

            expect(slugs).toEqual([expectedSlug]);
        });

        it("retries a slug the user already owns once with a suffix", async () => {
            const slugs = mockPageCreation("slug-conflict", "created");

            const page = await createPageFromTitle({ title: "Lab notes" });

            expect(slugs).toEqual(["lab-notes", "lab-notes-2"]);
            expect(page.slug).toBe("lab-notes-2");
        });

        it("reports a suffixed slug that is taken too", async () => {
            const slugs = mockPageCreation("slug-conflict", "slug-conflict");

            await expect(createPageFromTitle({ title: "Lab notes" })).rejects.toThrow("Page identifier must be unique");
            expect(slugs).toEqual(["lab-notes", "lab-notes-2"]);
        });
    });

    describe("deleteHistoryPage", () => {
        it("resolves without error on success", async () => {
            let requestedPageId: string | undefined;
            server.use(
                http.delete("/api/pages/{id}", ({ params, response }) => {
                    requestedPageId = params.id;
                    return response(204).empty();
                }),
            );

            await expect(deleteHistoryPage(TEST_PAGE_ID)).resolves.toBeUndefined();
            expect(requestedPageId).toBe(TEST_PAGE_ID);
        });

        it("throws on deletion error", async () => {
            server.use(
                http.delete("/api/pages/{id}", ({ response }) => {
                    return response("4XX").json({ err_msg: "Page not found", err_code: 404 }, { status: 404 });
                }),
            );

            await expect(deleteHistoryPage(TEST_PAGE_ID)).rejects.toThrow();
        });
    });
});
