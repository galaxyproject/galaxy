import { getFakeRegisteredUser } from "@tests/test-data";
import flushPromises from "flush-promises";
import { http as rawHttp } from "msw";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { purgeDatasetById, purgeHistoryById } from "./service";

const { server, http } = useServerMock();

describe("purging from the storage pages", () => {
    let userRequests: number;

    beforeEach(() => {
        setActivePinia(createPinia());
        userRequests = 0;
        server.use(
            http.get("/api/users/{user_id}", ({ response }) => {
                userRequests++;
                return response(200).json(getFakeRegisteredUser());
            }),
            http.delete("/api/histories/{history_id}", ({ response }) =>
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                response(200).json({ id: "history-1", purged: true } as any),
            ),
            rawHttp.delete("/api/datasets/:datasetId", () => HttpResponse.json({})),
        );
    });

    it.each([
        ["a history", () => purgeHistoryById("history-1")],
        ["a dataset", () => purgeDatasetById("dataset-1")],
    ])("refreshes the storage usage after purging %s", async (_item, purge) => {
        await purge();
        await flushPromises();

        expect(userRequests).toBe(1);
    });
});
