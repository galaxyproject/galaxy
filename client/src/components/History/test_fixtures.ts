import type { Decorator } from "@storybook/vue3-vite";
import { getFakeHistorySummaryExtended, getFakeRegisteredUser } from "@tests/test-data";
import { withCurrentHistory } from "@tests/test-data/currentHistory";
import { HttpResponse } from "msw";
import { h, onBeforeUnmount } from "vue";

import type { HistoryDetailed, HistoryDevDetailed, HistorySummaryExtended } from "@/api";
import { http } from "@/api/client/__mocks__/http";
import { useHistoryStore } from "@/stores/historyStore";

export const HISTORY_VIEWER = getFakeRegisteredUser({ username: "jules", email: "jules@example.org" });
export const ANALYSIS_HISTORY = getFakeHistorySummaryExtended({
    id: "a8d9234fce6710b2",
    url: "/api/histories/a8d9234fce6710b2",
    name: "RNA-seq analysis",
    user_id: HISTORY_VIEWER.id,
    count: 24,
    contents_active: { active: 24, deleted: 0, hidden: 0 },
});
export const QUALITY_HISTORY = getFakeHistorySummaryExtended({
    id: "b5e7623adf1890c4",
    url: "/api/histories/b5e7623adf1890c4",
    name: "Quality control",
    user_id: HISTORY_VIEWER.id,
    count: 8,
    contents_active: { active: 8, deleted: 0, hidden: 0 },
});

/** The legacy selection endpoints serialize the dev-detailed history view. */
function detailedHistory(history: HistorySummaryExtended): HistoryDevDetailed {
    return {
        ...history,
        contents_url: `/api/histories/${history.id}/contents`,
        create_time: "2026-01-01T00:00:00",
        genome_build: "?",
        importable: false,
        hid_counter: history.count + 1,
    };
}

/** The copy request asks for the detailed view rather than the summary view. */
function copiedHistoryDetails(history: HistorySummaryExtended): HistoryDetailed {
    return {
        ...detailedHistory(history),
        empty: history.count === 0,
        state: history.count === 0 ? "new" : "ok",
        state_details: { ok: history.count },
        state_ids: {
            ok: Array.from({ length: history.count }, (_, index) => (index + 1).toString(16).padStart(16, "0")),
        },
        username: history.user_id === null ? null : HISTORY_VIEWER.username,
    };
}

/** Fresh server state for a history menu; each mount resets its own copy/delete responses. */
export function historyOperationsStory(history: HistorySummaryExtended = ANALYSIS_HISTORY) {
    let storedHistories = new Map<string, HistorySummaryExtended>();
    let nextId = 0;
    const reset = () => {
        storedHistories = new Map([history, QUALITY_HISTORY].map((entry) => [entry.id, { ...entry }]));
        nextId = 0;
    };
    reset();
    const ownerId = history.user_id === null ? null : HISTORY_VIEWER.id;
    const currentHistories = () =>
        [...storedHistories.values()].filter((entry) => !entry.deleted && entry.user_id === ownerId);
    const findHistory = (id: string) => storedHistories.get(id) ?? history;
    const createHistory = (name: string, source?: HistorySummaryExtended) => {
        const created = getFakeHistorySummaryExtended({
            ...source,
            id: `c9f8102bad3476e${++nextId}`,
            name,
            user_id: ownerId,
            deleted: false,
            purged: false,
        });
        created.url = `/api/histories/${created.id}`;
        storedHistories.set(created.id, created);
        return created;
    };
    return {
        decorators: [
            withCurrentHistory(history.user_id === ownerId ? history : QUALITY_HISTORY),
            ((story) => ({
                setup() {
                    reset();
                    const store = useHistoryStore();
                    const previousCount = store.totalHistoryCount;
                    store.totalHistoryCount = currentHistories().length;
                    onBeforeUnmount(() => {
                        store.totalHistoryCount = previousCount;
                    });
                },
                render() {
                    return h(story());
                },
            })) as Decorator,
        ],
        parameters: {
            msw: {
                handlers: {
                    historyCount: http.get("/api/histories/count", ({ response }) =>
                        response(200).json(currentHistories().length),
                    ),
                    history: http.get("/api/histories/{history_id}", ({ params, response }) =>
                        response(200).json(findHistory(params.history_id)),
                    ),
                    histories: http.get("/api/histories", ({ response }) => response(200).json(currentHistories())),
                    copyHistory: http.post("/api/histories", async ({ request, response }) => {
                        // This endpoint accepts JSON as well as the documented form payload.
                        const payload: unknown = await (request as Request).json();
                        if (
                            !payload ||
                            typeof payload !== "object" ||
                            !("name" in payload) ||
                            typeof payload.name !== "string" ||
                            !("history_id" in payload) ||
                            typeof payload.history_id !== "string"
                        ) {
                            throw new Error("History copy fixture expects a JSON name and source history_id.");
                        }
                        return response(200).json(
                            copiedHistoryDetails(createHistory(payload.name, findHistory(payload.history_id))),
                        );
                    }),
                    deleteHistory: http.delete("/api/histories/{history_id}", ({ params, request, response }) => {
                        const deleted = {
                            ...findHistory(params.history_id),
                            deleted: true,
                            purged: new URL(request.url).searchParams.get("purge") === "true",
                        };
                        storedHistories.set(deleted.id, deleted);
                        return response(200).json(deleted);
                    }),
                    // These legacy controller endpoints are not described by OpenAPI.
                    resumePausedJobs: http.untyped.get("/history/resume_paused_jobs", () =>
                        HttpResponse.json({ message: "Your jobs have been resumed.", status: "success" }),
                    ),
                    selectHistory: http.untyped.get("/history/set_as_current", ({ request }) =>
                        HttpResponse.json(
                            detailedHistory(findHistory(new URL(request.url).searchParams.get("id") || history.id)),
                        ),
                    ),
                    createCurrentHistory: http.untyped.get("/history/create_new_current", ({ request }) =>
                        HttpResponse.json(
                            detailedHistory(
                                createHistory(new URL(request.url).searchParams.get("name") || "Unnamed history"),
                            ),
                        ),
                    ),
                },
            },
        },
    };
}
