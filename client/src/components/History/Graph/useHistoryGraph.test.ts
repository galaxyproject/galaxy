import flushPromises from "flush-promises";
import type * as PiniaModule from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed, type EffectScope, effectScope, nextTick, ref } from "vue";

import type * as MapperModule from "./historyGraphMapper";

// Mock all of useHistoryGraph's dependencies before importing it. Lets the
// tests script update_time changes, SSE config, ownership, and the data
// composable's return shape independently.

const mockHistory = ref<{ id: string; update_time: string; user_id?: string | null } | null>(null);
vi.mock("@/composables/detailedHistory", () => ({
    useExtendedHistory: () => ({ history: mockHistory }),
}));

const mockConfig = ref<{ enable_sse_updates: boolean }>({ enable_sse_updates: false });
vi.mock("@/composables/config", () => ({
    useConfig: () => ({ config: mockConfig }),
}));

const mockCurrentUser = ref<{ id: string } | null>({ id: "u1" });
vi.mock("@/stores/userStore", () => ({
    useUserStore: () => ({ currentUser: mockCurrentUser }),
}));

// storeToRefs() rejects plain objects in jsdom; passthrough works because the
// mocked store above already returns refs directly.
vi.mock("pinia", async () => {
    const actual = await vi.importActual<typeof PiniaModule>("pinia");
    return { ...actual, storeToRefs: (store: unknown) => store };
});

const mockUserOwns = vi.fn<(user: unknown, history: unknown) => boolean>(() => true);
vi.mock("@/api", () => ({
    userOwnsHistory: (...args: unknown[]) => mockUserOwns(args[0], args[1]),
}));

const subscribe = vi.fn<(id: string) => void>();
const unsubscribe = vi.fn<(id: string) => void>();
vi.mock("@/composables/useNotificationSSE", () => ({
    addHistoryViewerSubscription: (id: string) => subscribe(id),
    removeHistoryViewerSubscription: (id: string) => unsubscribe(id),
}));

const mockGraphData = ref<unknown>(null);
const mockRefetch = vi.fn();
vi.mock("./useHistoryGraphData", () => ({
    useHistoryGraphData: () => ({
        graphData: mockGraphData,
        loading: ref(false),
        error: ref(null),
        refetch: mockRefetch,
    }),
}));

// Stub the mappers so the projection tests don't depend on the real mapper.
vi.mock("./historyGraphMapper", async () => {
    const actual = await vi.importActual<typeof MapperModule>("./historyGraphMapper");
    return {
        ...actual,
        mapNodes: vi.fn((nodes: unknown[]) =>
            nodes.map((n) => {
                const node = n as { id: string; src: string };
                return { id: `${node.src}:${node.id}`, data: { src: node.src, itemId: node.id } };
            }),
        ),
        mapEdges: vi.fn(() => []),
    };
});

const { useHistoryGraph: realUseHistoryGraph } = await import("./useHistoryGraph");

// Each test runs the composable inside its own effectScope so watchers from
// earlier tests don't fire on shared mock state.
let scope: EffectScope | null = null;
function useHistoryGraph(...args: Parameters<typeof realUseHistoryGraph>) {
    scope = effectScope();
    return scope.run(() => realUseHistoryGraph(...args))!;
}

function resetMocks() {
    mockHistory.value = null;
    mockConfig.value = { enable_sse_updates: false };
    mockCurrentUser.value = { id: "u1" };
    mockGraphData.value = null;
    mockUserOwns.mockReset();
    mockUserOwns.mockReturnValue(true);
    mockRefetch.mockClear();
    subscribe.mockClear();
    unsubscribe.mockClear();
}

describe("useHistoryGraph", () => {
    beforeEach(resetMocks);
    afterEach(() => {
        scope?.stop();
        scope = null;
    });

    describe("projections", () => {
        it("returns empty arrays when no graph data is loaded", () => {
            const { graphNodes, graphEdges, toolExecutionNodes, isTruncated } = useHistoryGraph(
                ref("h1"),
                ref(undefined),
                ref(undefined),
            );
            expect(graphNodes.value).toEqual([]);
            expect(graphEdges.value).toEqual([]);
            expect(toolExecutionNodes.value).toEqual([]);
            expect(isTruncated.value).toBe(false);
        });

        it("maps nodes and filters tool_request nodes for the executions list", () => {
            mockGraphData.value = {
                nodes: [
                    { id: "1", src: "hda" },
                    { id: "2", src: "tool_request" },
                    { id: "3", src: "hdca" },
                    { id: "4", src: "tool_request" },
                ],
                edges: [],
                truncated: { item_count_capped: false },
            };
            const { graphNodes, toolExecutionNodes } = useHistoryGraph(ref("h1"), ref(undefined), ref(undefined));
            expect(graphNodes.value).toHaveLength(4);
            expect(toolExecutionNodes.value.map((n) => n.id)).toEqual(["tool_request:2", "tool_request:4"]);
        });

        it("surfaces the truncation flag from the API payload", () => {
            mockGraphData.value = { nodes: [], edges: [], truncated: { item_count_capped: true } };
            const { isTruncated } = useHistoryGraph(ref("h1"), ref(undefined), ref(undefined));
            expect(isTruncated.value).toBe(true);
        });

        it("derives focusNodeId from (seedSrc, seedId) using the mapper's nodeKey encoding", () => {
            const { focusNodeId } = useHistoryGraph(ref("h1"), ref("hda"), ref("d-7"));
            expect(focusNodeId.value).toBe("hda:d-7");
        });

        it("returns null focusNodeId when either seed component is missing", () => {
            const seedSrc = ref<string | undefined>(undefined);
            const seedId = ref<string | undefined>(undefined);
            const { focusNodeId } = useHistoryGraph(ref("h1"), seedSrc, seedId);
            expect(focusNodeId.value).toBeNull();
            seedSrc.value = "hda";
            expect(focusNodeId.value).toBeNull();
            seedId.value = "d-7";
            expect(focusNodeId.value).toBe("hda:d-7");
        });
    });

    describe("update_time refetch", () => {
        it("calls refetch when update_time changes from one value to another", async () => {
            mockHistory.value = { id: "h1", update_time: "t1" };
            useHistoryGraph(ref("h1"), ref(undefined), ref(undefined));
            await nextTick();
            mockRefetch.mockClear();
            mockHistory.value = { id: "h1", update_time: "t2" };
            await nextTick();
            expect(mockRefetch).toHaveBeenCalledTimes(1);
        });

        it("does not refetch on the initial undefined → first-value transition", async () => {
            useHistoryGraph(ref("h1"), ref(undefined), ref(undefined));
            await nextTick();
            mockRefetch.mockClear();
            mockHistory.value = { id: "h1", update_time: "t1" };
            await nextTick();
            expect(mockRefetch).not.toHaveBeenCalled();
        });
    });

    describe("SSE viewer subscription", () => {
        it("does not subscribe when SSE is disabled in config", async () => {
            mockConfig.value = { enable_sse_updates: false };
            mockHistory.value = { id: "h1", update_time: "t1", user_id: "other" };
            useHistoryGraph(ref("h1"), ref(undefined), ref(undefined));
            await flushPromises();
            expect(subscribe).not.toHaveBeenCalled();
        });

        it("does not subscribe when the current user owns the history", async () => {
            mockConfig.value = { enable_sse_updates: true };
            mockHistory.value = { id: "h1", update_time: "t1", user_id: "u1" };
            mockUserOwns.mockReturnValue(true);
            useHistoryGraph(ref("h1"), ref(undefined), ref(undefined));
            await flushPromises();
            expect(subscribe).not.toHaveBeenCalled();
        });

        it("subscribes when SSE is enabled and the user doesn't own the history", async () => {
            mockConfig.value = { enable_sse_updates: true };
            mockHistory.value = { id: "h1", update_time: "t1", user_id: "owner" };
            mockUserOwns.mockReturnValue(false);
            useHistoryGraph(ref("h1"), ref(undefined), ref(undefined));
            await flushPromises();
            expect(subscribe).toHaveBeenCalledWith("h1");
        });

        it("unsubscribes when the historyId changes", async () => {
            mockConfig.value = { enable_sse_updates: true };
            mockHistory.value = { id: "h1", update_time: "t1", user_id: "owner" };
            mockUserOwns.mockReturnValue(false);
            const historyId = ref("h1");
            useHistoryGraph(historyId, ref(undefined), ref(undefined));
            await flushPromises();
            subscribe.mockClear();
            historyId.value = "h2";
            await flushPromises();
            expect(unsubscribe).toHaveBeenCalledWith("h1");
            expect(subscribe).toHaveBeenCalledWith("h2");
        });
    });

    describe("return shape", () => {
        it("exposes history, loading, error, refetch alongside the projections", () => {
            const result = useHistoryGraph(ref("h1"), ref(undefined), ref(undefined));
            expect(Object.keys(result).sort()).toEqual(
                [
                    "error",
                    "focusNodeId",
                    "graphEdges",
                    "graphNodes",
                    "history",
                    "isTruncated",
                    "loading",
                    "refetch",
                    "toolExecutionNodes",
                ].sort(),
            );
            // Sanity: history is the same reactive ref the dependency exposes.
            expect(result.history).toBe(mockHistory);
            // Sanity: computed projections are computed refs (read via .value).
            const _: unknown = computed(() => result.graphNodes.value.length);
            expect(_).toBeDefined();
        });
    });
});
