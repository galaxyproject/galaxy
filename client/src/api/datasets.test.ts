import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { copyDatasets } from "./datasets";

const { server } = useServerMock();

describe("copyDatasets", () => {
    it("copies all dataset ids to the target history", async () => {
        const copiedDatasetIds: unknown[] = [];

        let receivedHistoryId;

        server.use(
            http.post("/api/histories/:history_id/contents/datasets", async ({ params, request }) => {
                const body = (await request.json()) as { content: unknown };

                receivedHistoryId = params.history_id;

                copiedDatasetIds.push(body.content);

                return HttpResponse.json({ id: body.content });
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

    it("reports failed dataset ids when some copies fail", async () => {
        server.use(
            http.post("/api/histories/:history_id/contents/datasets", async ({ request }) => {
                const body = (await request.json()) as { content: unknown };

                if (body.content === "dataset-b") {
                    return HttpResponse.json({ err_msg: "Copy failed" }, { status: 500 });
                }

                return HttpResponse.json({ id: body.content });
            }),
        );

        const result = await copyDatasets(["dataset-a", "dataset-b"], "target-history");

        expect(result).toEqual({
            copiedDatasets: [{ id: "dataset-a" }],
            failedDatasetIds: ["dataset-b"],
        });
    });
});
