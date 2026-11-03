import { runInTestScope } from "@tests/vitest/effectScope";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";
import { ref, watch } from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import type { HistoryGraphResponse } from "./historyGraphMapper";
import { useHistoryGraphData } from "./useHistoryGraphData";

const { server, http } = useServerMock();

const EMPTY_GRAPH: HistoryGraphResponse = {
    nodes: [],
    edges: [],
    truncated: { item_count_capped: false, scope_type: "recent" },
};

interface GraphRequest {
    historyId: string;
    limit: string | null;
    seedSrc: string | null;
    seedId: string | null;
}

function respondWithGraph(graph: HistoryGraphResponse = EMPTY_GRAPH) {
    const requestSpy = vi.fn<(request: GraphRequest) => void>();
    server.use(
        http.get("/api/histories/{history_id}/graph", ({ params, query, response }) => {
            requestSpy({
                historyId: params.history_id,
                limit: query.get("limit"),
                seedSrc: query.get("seed_src"),
                seedId: query.get("seed_id"),
            });
            return response(200).json(graph);
        }),
    );
    return requestSpy;
}

function respondWithError(message: string) {
    server.use(
        http.get("/api/histories/{history_id}/graph", ({ response }) =>
            response("4XX").json({ err_msg: message, err_code: 0 }, { status: 404 }),
        ),
    );
}

function createGraphData(...args: Parameters<typeof useHistoryGraphData>) {
    return runInTestScope(() => useHistoryGraphData(...args));
}

describe("useHistoryGraphData", () => {
    describe("requests", () => {
        it("fetches the history graph with the limit as soon as it is called", async () => {
            const requests = respondWithGraph();

            createGraphData(ref("h1"), ref(100));
            await flushPromises();

            expect(requests).toHaveBeenCalledTimes(1);
            expect(requests).toHaveBeenCalledWith(expect.objectContaining({ historyId: "h1", limit: "100" }));
        });

        it("omits seed_src and seed_id when no seed refs are given", async () => {
            const requests = respondWithGraph();

            createGraphData(ref("h1"), ref(100));
            await flushPromises();

            expect(requests).toHaveBeenCalledTimes(1);
            expect(requests).toHaveBeenCalledWith(expect.objectContaining({ seedSrc: null, seedId: null }));
        });

        it("includes seed_src and seed_id when both seed refs are set", async () => {
            const requests = respondWithGraph();

            createGraphData(ref("h1"), ref(100), ref("hda"), ref("d-7"));
            await flushPromises();

            expect(requests).toHaveBeenCalledTimes(1);
            expect(requests).toHaveBeenCalledWith(expect.objectContaining({ seedSrc: "hda", seedId: "d-7" }));
        });

        it("refetches when historyId changes", async () => {
            const requests = respondWithGraph();
            const historyId = ref("h1");
            createGraphData(historyId, ref(100));
            await flushPromises();
            requests.mockClear();

            historyId.value = "h2";
            await flushPromises();

            expect(requests).toHaveBeenCalledTimes(1);
            expect(requests).toHaveBeenCalledWith(expect.objectContaining({ historyId: "h2" }));
        });

        it("refetches when limit changes", async () => {
            const requests = respondWithGraph();
            const limit = ref(100);
            createGraphData(ref("h1"), limit);
            await flushPromises();
            requests.mockClear();

            limit.value = 250;
            await flushPromises();

            expect(requests).toHaveBeenCalledTimes(1);
            expect(requests).toHaveBeenCalledWith(expect.objectContaining({ limit: "250" }));
        });

        it("exposes refetch() for manual refresh", async () => {
            const requests = respondWithGraph();
            const { refetch } = createGraphData(ref("h1"), ref(100));
            await flushPromises();
            requests.mockClear();

            await refetch();

            expect(requests).toHaveBeenCalledTimes(1);
            expect(requests).toHaveBeenCalledWith(expect.objectContaining({ historyId: "h1", limit: "100" }));
        });
    });

    describe("state", () => {
        it("exposes the graph with no error once the first fetch succeeds", async () => {
            respondWithGraph();

            const { graphData, error, loading } = createGraphData(ref("h1"), ref(100));
            await flushPromises();

            expect(loading.value).toBe(false);
            expect(error.value).toBeNull();
            expect(graphData.value).toEqual(EMPTY_GRAPH);
        });

        it("clears a previous error when a refetch succeeds", async () => {
            respondWithError("history not found");
            const { error, refetch } = createGraphData(ref("h1"), ref(100));
            await flushPromises();
            expect(error.value).toBe("history not found");

            respondWithGraph();
            await refetch();

            expect(error.value).toBeNull();
        });

        it("shows loading while the first fetch is in flight", async () => {
            respondWithGraph();

            const { loading } = createGraphData(ref("h1"), ref(100));

            expect(loading.value).toBe(true);
            await flushPromises();
            expect(loading.value).toBe(false);
        });

        it("keeps loading false on refetch when data is already loaded", async () => {
            // The HistoryGraphView template swaps the entire graph subtree for a
            // spinner whenever `loading` is true, which unmounts GraphView and
            // resets pan/zoom. A background refetch must not flip `loading` so
            // the existing view survives until fresh data arrives.
            respondWithGraph();
            const { loading, refetch } = createGraphData(ref("h1"), ref(100));
            await flushPromises();
            expect(loading.value).toBe(false);

            const loadingChanges: boolean[] = [];
            runInTestScope(() => watch(loading, (value) => loadingChanges.push(value), { flush: "sync" }));
            await refetch();

            expect(loadingChanges).toEqual([]);
            expect(loading.value).toBe(false);
        });

        it("reports the API error message and no graph when the first fetch fails", async () => {
            respondWithError("history not found");

            const { graphData, error } = createGraphData(ref("missing"), ref(100));
            await flushPromises();

            expect(error.value).toBe("history not found");
            expect(graphData.value).toBeNull();
        });

        it("clears the loaded graph when a refetch fails", async () => {
            respondWithGraph();
            const { graphData, error, refetch } = createGraphData(ref("h1"), ref(100));
            await flushPromises();
            expect(graphData.value).toEqual(EMPTY_GRAPH);

            respondWithError("history not found");
            await refetch();

            expect(error.value).toBe("history not found");
            expect(graphData.value).toBeNull();
        });
    });
});
