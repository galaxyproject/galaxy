import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import { useHistoryGraphData } from "./useHistoryGraphData";

const { server, http } = useServerMock();

interface CapturedCall {
    historyId: string;
    query: URLSearchParams;
}
const captured = vi.fn<(args: CapturedCall) => void>();

describe("useHistoryGraphData", () => {
    beforeEach(() => {
        captured.mockClear();
        server.use(
            http.get("/api/histories/{history_id}/graph", ({ response, params, query }) => {
                captured({ historyId: params.history_id as string, query: query as unknown as URLSearchParams });
                return response(200).json({
                    nodes: [],
                    edges: [],
                    truncated: { item_count_capped: false },
                } as never);
            }),
        );
    });

    it("fetches immediately on mount", async () => {
        useHistoryGraphData(ref("h1"), ref(100));
        await flushPromises();
        expect(captured).toHaveBeenCalledTimes(1);
        expect(captured.mock.calls[0]![0].historyId).toBe("h1");
        expect(captured.mock.calls[0]![0].query.get("limit")).toBe("100");
    });

    it("omits seed_src / seed_id when both are undefined", async () => {
        useHistoryGraphData(ref("h1"), ref(100));
        await flushPromises();
        const q = captured.mock.calls[0]![0].query;
        expect(q.get("seed_src")).toBeNull();
        expect(q.get("seed_id")).toBeNull();
    });

    it("includes seed_src and seed_id when both refs are set", async () => {
        useHistoryGraphData(ref("h1"), ref(100), ref("hda"), ref("d-7"));
        await flushPromises();
        const q = captured.mock.calls[0]![0].query;
        expect(q.get("seed_src")).toBe("hda");
        expect(q.get("seed_id")).toBe("d-7");
    });

    it("refetches when historyId changes", async () => {
        const id = ref("h1");
        useHistoryGraphData(id, ref(100));
        await flushPromises();
        captured.mockClear();
        id.value = "h2";
        await flushPromises();
        expect(captured).toHaveBeenCalledTimes(1);
        expect(captured.mock.calls[0]![0].historyId).toBe("h2");
    });

    it("refetches when limit changes", async () => {
        const limit = ref(100);
        useHistoryGraphData(ref("h1"), limit);
        await flushPromises();
        captured.mockClear();
        limit.value = 250;
        await flushPromises();
        expect(captured.mock.calls[0]![0].query.get("limit")).toBe("250");
    });

    it("exposes refetch() for manual refresh", async () => {
        const { refetch } = useHistoryGraphData(ref("h1"), ref(100));
        await flushPromises();
        captured.mockClear();
        refetch();
        await flushPromises();
        expect(captured).toHaveBeenCalledTimes(1);
    });

    it("sets graphData on success and clears error", async () => {
        const { graphData, error, loading } = useHistoryGraphData(ref("h1"), ref(100));
        await flushPromises();
        expect(loading.value).toBe(false);
        expect(error.value).toBeNull();
        expect(graphData.value).not.toBeNull();
    });

    it("keeps loading false on refetch when data is already loaded", async () => {
        // The HistoryGraphView template swaps the entire graph subtree for a
        // spinner whenever `loading` is true, which unmounts GraphView and
        // resets pan/zoom. A background refetch must not flip `loading` so
        // the existing view survives until fresh data arrives.
        const { loading, refetch } = useHistoryGraphData(ref("h1"), ref(100));
        await flushPromises();
        expect(loading.value).toBe(false);

        let loadingDuringRefetch = false;
        const stopWatch = vi.fn(() => {
            if (loading.value) {
                loadingDuringRefetch = true;
            }
        });
        // Snapshot the ref via a synchronous tick around refetch().
        const promise = refetch();
        stopWatch();
        await promise;
        await flushPromises();

        expect(loadingDuringRefetch).toBe(false);
        expect(loading.value).toBe(false);
    });

    it("sets error and clears graphData when the API replies with an error", async () => {
        server.use(
            http.get("/api/histories/{history_id}/graph", ({ response }) =>
                response("4XX").json({ err_msg: "history not found", err_code: 0 }, { status: 404 }),
            ),
        );
        const { graphData, error } = useHistoryGraphData(ref("missing"), ref(100));
        await flushPromises();
        expect(error.value).toMatch(/history not found/);
        expect(graphData.value).toBeNull();
    });
});
