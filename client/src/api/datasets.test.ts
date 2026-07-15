import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { copyDatasets } from "./datasets";

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
                    return response("5XX").json({ err_msg: "Copy failed" }, { status: 500 });
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
