import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import type { HistoryNotebookDetails, HistoryNotebookSummary } from "./historyNotebooks";
import {
    createHistoryNotebook,
    deleteHistoryNotebook,
    fetchHistoryNotebook,
    fetchHistoryNotebooks,
    updateHistoryNotebook,
} from "./historyNotebooks";

const { server, http } = useServerMock();

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

describe("historyNotebooks API", () => {
    describe("fetchHistoryNotebooks", () => {
        it("returns list of notebooks for a history", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks", ({ params, response }) => {
                    expect(params.history_id).toBe(TEST_HISTORY_ID);
                    return response(200).json([TEST_NOTEBOOK_SUMMARY]);
                }),
            );

            const result = await fetchHistoryNotebooks(TEST_HISTORY_ID);

            expect(result).toEqual([TEST_NOTEBOOK_SUMMARY]);
        });

        it("returns empty list when history has no notebooks", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response(200).json([]);
                }),
            );

            const result = await fetchHistoryNotebooks(TEST_HISTORY_ID);

            expect(result).toEqual([]);
        });

        it("throws on server error", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response("4XX").json({ err_msg: "History not found", err_code: 404 }, { status: 404 });
                }),
            );

            await expect(fetchHistoryNotebooks(TEST_HISTORY_ID)).rejects.toThrow("History not found");
        });
    });

    describe("fetchHistoryNotebook", () => {
        it("returns notebook details by id", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks/{notebook_id}", ({ params, response }) => {
                    expect(params.history_id).toBe(TEST_HISTORY_ID);
                    expect(params.notebook_id).toBe(TEST_NOTEBOOK_ID);
                    return response(200).json(TEST_NOTEBOOK_DETAILS);
                }),
            );

            const result = await fetchHistoryNotebook(TEST_HISTORY_ID, TEST_NOTEBOOK_ID);

            expect(result).toEqual(TEST_NOTEBOOK_DETAILS);
        });

        it("throws on notebook not found", async () => {
            server.use(
                http.get("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response("4XX").json({ err_msg: "Notebook not found", err_code: 404 }, { status: 404 });
                }),
            );

            await expect(fetchHistoryNotebook(TEST_HISTORY_ID, "nonexistent")).rejects.toThrow("Notebook not found");
        });
    });

    describe("createHistoryNotebook", () => {
        const CREATE_PAYLOAD = {
            content: "# New Notebook\n\nInitial content.",
            content_format: "markdown" as const,
            title: "New Notebook",
        };

        it("returns created notebook details", async () => {
            server.use(
                http.post("/api/histories/{history_id}/notebooks", ({ params, response }) => {
                    expect(params.history_id).toBe(TEST_HISTORY_ID);
                    return response(200).json({
                        ...TEST_NOTEBOOK_DETAILS,
                        title: "New Notebook",
                        content: "# New Notebook\n\nInitial content.",
                    });
                }),
            );

            const result = await createHistoryNotebook(TEST_HISTORY_ID, CREATE_PAYLOAD);

            expect(result.title).toBe("New Notebook");
            expect(result.content).toBe("# New Notebook\n\nInitial content.");
            expect(result.history_id).toBe(TEST_HISTORY_ID);
            expect(result.id).toBe(TEST_NOTEBOOK_ID);
        });

        it("throws on creation error", async () => {
            server.use(
                http.post("/api/histories/{history_id}/notebooks", ({ response }) => {
                    return response("4XX").json({ err_msg: "Cannot create notebook", err_code: 400 }, { status: 400 });
                }),
            );

            await expect(createHistoryNotebook(TEST_HISTORY_ID, CREATE_PAYLOAD)).rejects.toThrow(
                "Cannot create notebook",
            );
        });
    });

    describe("updateHistoryNotebook", () => {
        const UPDATE_PAYLOAD = {
            content: "# Updated Content\n\nRevised analysis.",
            content_format: "markdown" as const,
            title: "Updated Title",
        };

        it("returns updated notebook details", async () => {
            server.use(
                http.put("/api/histories/{history_id}/notebooks/{notebook_id}", ({ params, response }) => {
                    expect(params.history_id).toBe(TEST_HISTORY_ID);
                    expect(params.notebook_id).toBe(TEST_NOTEBOOK_ID);
                    return response(200).json({
                        ...TEST_NOTEBOOK_DETAILS,
                        title: "Updated Title",
                        content: "# Updated Content\n\nRevised analysis.",
                        update_time: "2025-06-16T09:00:00Z",
                    });
                }),
            );

            const result = await updateHistoryNotebook(TEST_HISTORY_ID, TEST_NOTEBOOK_ID, UPDATE_PAYLOAD);

            expect(result.title).toBe("Updated Title");
            expect(result.content).toBe("# Updated Content\n\nRevised analysis.");
            expect(result.update_time).toBe("2025-06-16T09:00:00Z");
        });

        it("throws on update error", async () => {
            server.use(
                http.put("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response("4XX").json({ err_msg: "Notebook is deleted", err_code: 400 }, { status: 400 });
                }),
            );

            await expect(updateHistoryNotebook(TEST_HISTORY_ID, TEST_NOTEBOOK_ID, UPDATE_PAYLOAD)).rejects.toThrow(
                "Notebook is deleted",
            );
        });
    });

    describe("deleteHistoryNotebook", () => {
        it("resolves without error on success", async () => {
            server.use(
                http.delete("/api/histories/{history_id}/notebooks/{notebook_id}", ({ params, response }) => {
                    expect(params.history_id).toBe(TEST_HISTORY_ID);
                    expect(params.notebook_id).toBe(TEST_NOTEBOOK_ID);
                    return response(204).empty();
                }),
            );

            await expect(deleteHistoryNotebook(TEST_HISTORY_ID, TEST_NOTEBOOK_ID)).resolves.toBeUndefined();
        });

        it("throws on deletion error", async () => {
            server.use(
                http.delete("/api/histories/{history_id}/notebooks/{notebook_id}", ({ response }) => {
                    return response("4XX").json({ err_msg: "Notebook not found", err_code: 404 }, { status: 404 });
                }),
            );

            await expect(deleteHistoryNotebook(TEST_HISTORY_ID, TEST_NOTEBOOK_ID)).rejects.toThrow(
                "Notebook not found",
            );
        });
    });
});
