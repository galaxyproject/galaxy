import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { copyDatasets, copyHistoryItems } from "./datasets";

const { server, http } = useServerMock();

describe("copyDatasets", () => {
    it("copies all dataset ids to the target history", async () => {
        const copiedDatasetIds: unknown[] = [];

        let receivedHistoryId;

        server.use(
            http.post("/api/histories/{history_id}/contents/{type}s", async ({ params, request, response }) => {
                const body = (await request.json()) as { content: unknown };

                receivedHistoryId = params.history_id;

                copiedDatasetIds.push(body.content);

                return response(200).json({ id: body.content } as any);
            }),
        );

        const result = await copyDatasets(["dataset-a", "dataset-b"], "target-history");
        expect(receivedHistoryId).toBe("target-history");

        expect(copiedDatasetIds).toEqual(["dataset-a", "dataset-b"]);
        expect(result).toEqual({
            copiedDatasets: [{ id: "dataset-a" }, { id: "dataset-b" }],
            failedDatasetIds: [],
        });
    });

    it("preserves result order and limits concurrent requests across batches", async () => {
        let inFlight = 0;
        let peakInFlight = 0;

        server.use(
            http.post("/api/histories/{history_id}/contents/{type}s", async ({ request, response }) => {
                const body = (await request.json()) as { content: unknown };
                inFlight++;
                peakInFlight = Math.max(peakInFlight, inFlight);

                await new Promise((resolve) => setTimeout(resolve, 1));
                inFlight--;

                if (body.content === "dataset-7") {
                    return response("5XX").json({ err_code: 500, err_msg: "Copy failed" }, { status: 500 });
                }

                return response(200).json({ id: body.content } as any);
            }),
        );

        const datasetIds = Array.from({ length: 7 }, (_, index) => `dataset-${index + 1}`);
        const result = await copyDatasets(datasetIds, "target-history");

        expect(result).toEqual({
            copiedDatasets: datasetIds.slice(0, 6).map((id) => ({ id })),
            failedDatasetIds: ["dataset-7"],
        });
        expect(peakInFlight).toBe(5);
    });
});

describe("copyHistoryItems", () => {
    it("copies datasets and collections using their matching content type and source", async () => {
        const requests: Array<{ pathname: string; body: Record<string, unknown> }> = [];

        server.use(
            http.post("/api/histories/{history_id}/contents/{type}s", async ({ request, response }) => {
                requests.push({
                    pathname: new URL(request.url).pathname,
                    body: (await request.json()) as Record<string, unknown>,
                });

                return response(200).json({ id: requests.at(-1)?.body.content } as never);
            }),
        );

        const result = await copyHistoryItems(
            [
                { id: "dataset-a", history_content_type: "dataset" },
                { id: "collection-a", history_content_type: "dataset_collection" },
            ],
            "target-history",
        );

        expect(requests).toEqual([
            {
                pathname: "/api/histories/target-history/contents/datasets",
                body: expect.objectContaining({ content: "dataset-a", source: "hda", type: "dataset" }),
            },
            {
                pathname: "/api/histories/target-history/contents/dataset_collections",
                body: expect.objectContaining({
                    content: "collection-a",
                    source: "hdca",
                    type: "dataset_collection",
                }),
            },
        ]);
        expect(result).toEqual({
            copiedItems: [{ id: "dataset-a" }, { id: "collection-a" }],
            failedItemIds: [],
        });
    });
});
