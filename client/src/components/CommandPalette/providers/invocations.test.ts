import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getData as getInvocationsData } from "@/components/Grid/configs/invocations";
import { useInvocationStore } from "@/stores/invocationStore";

import type { PaletteContext } from "../types";
import { invocationsProvider } from "./invocations";
import { resetListRefreshTracking } from "./refresh";
import type { ScopeDefinition } from "./scopes";

vi.mock("@/components/Grid/configs/invocations", () => ({
    getData: vi.fn(),
}));

const WORKFLOW_NAMES: Record<string, string> = { wf1: "Variant calling", wf2: "RNA-seq" };
const HISTORY_NAMES: Record<string, string> = { h1: "My analysis", h2: "Scratch" };

vi.mock("@/stores/workflowStore", () => ({
    useWorkflowStore: () => ({
        getStoredWorkflowNameByInstanceId: (id: string, fallback = "...") => WORKFLOW_NAMES[id] ?? fallback,
        // awaited by `fetchLatestInvocations` so the names are there to render
        fetchWorkflowForInstanceIdCached: async () => undefined,
    }),
}));

vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: () => ({
        getHistoryById: (id: string) => (HISTORY_NAMES[id] ? { id, name: HISTORY_NAMES[id] } : null),
        loadHistoryById: async () => undefined,
    }),
}));

const recentItems = vi.fn(() => [] as { type: string; id: string; name: string; to?: string }[]);

vi.mock("@/composables/useRecentPaletteItems", () => ({
    useRecentPaletteItems: () => ({ recentItems, addRecentItem: vi.fn(), clearRecentItems: vi.fn() }),
}));

const INVOCATIONS = [
    {
        id: "inv1",
        workflow_id: "wf1",
        history_id: "h1",
        state: "scheduled",
        create_time: "2026-08-30T10:00:00",
        update_time: "2026-08-30T10:00:00",
    },
    {
        id: "inv2",
        workflow_id: "wf2",
        history_id: "h2",
        state: "new",
        create_time: "2026-08-29T10:00:00",
        update_time: "2026-08-29T10:00:00",
    },
    {
        id: "inv3",
        workflow_id: "unknown_wf",
        history_id: "unknown_history",
        state: "cancelled",
        create_time: "2026-08-28T10:00:00",
        update_time: "2026-08-28T10:00:00",
    },
];

const SCOPE: ScopeDefinition = { key: "i", label: "Invocations", providerId: "invocations" };

function makeCtx(): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAdmin: false, isAnonymous: false };
}

describe("invocationsProvider", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        recentItems.mockReturnValue([]);
        resetListRefreshTracking();
        vi.mocked(getInvocationsData).mockReset();
        vi.mocked(getInvocationsData).mockResolvedValue([INVOCATIONS, INVOCATIONS.length] as never);
    });

    it("maps invocations to items with workflow, state, date and history", async () => {
        const sections = (await invocationsProvider.searchScoped?.(SCOPE, "variant", makeCtx())) ?? [];
        const items = sections[0]?.items ?? [];
        expect(items).toHaveLength(1);
        expect(items[0]?.id).toBe("invocations:inv1");
        expect(items[0]?.title).toBe("Variant calling");
        expect(items[0]?.subtitle).toContain("scheduled");
        expect(items[0]?.subtitle).toContain("2026");
        expect(items[0]?.subtitle).toContain("My analysis");
        expect(items[0]?.to).toBe("/workflows/invocations/inv1");
    });

    it("falls back to the invocation id when the workflow name is unknown", async () => {
        const sections = await invocationsProvider.searchScoped?.(SCOPE, "", makeCtx());
        const latest = sections?.find((s) => s.id === "latest");
        expect(latest?.items.map((i) => i.title)).toEqual(["Variant calling", "RNA-seq", "Invocation inv3"]);
    });

    it("filters client-side by history name too", async () => {
        const sections = (await invocationsProvider.searchScoped?.(SCOPE, "scratch", makeCtx())) ?? [];
        expect(sections[0]?.items.map((i) => i.id)).toEqual(["invocations:inv2"]);
    });

    it("filters the cache in the unscoped fan-out and never fetches there", async () => {
        // nothing cached yet: the fan-out contributes nothing rather than fetching
        expect(await invocationsProvider.search("variant", makeCtx())).toEqual([]);
        expect(getInvocationsData).not.toHaveBeenCalled();

        await useInvocationStore().fetchLatestInvocations(15);
        vi.mocked(getInvocationsData).mockClear();

        const items = await invocationsProvider.search("variant", makeCtx());

        expect(items.map((i) => i.id)).toEqual(["invocations:inv1"]);
        expect(getInvocationsData).not.toHaveBeenCalled();
    });

    it("renders the store cache without fetching again", async () => {
        const invocationStore = useInvocationStore();
        await invocationStore.fetchLatestInvocations(15);
        vi.mocked(getInvocationsData).mockClear();

        const items = invocationsProvider.emptyQueryItems?.(makeCtx()) ?? [];
        expect(items.map((i) => i.id)).toEqual(["invocations:inv1", "invocations:inv2", "invocations:inv3"]);
        expect(getInvocationsData).not.toHaveBeenCalled();
    });

    it("shows remembered invocations above the latest ones", async () => {
        recentItems.mockReturnValue([{ type: "invocation", id: "inv2", name: "RNA-seq" }]);
        const sections = (await invocationsProvider.searchScoped?.(SCOPE, "", makeCtx())) ?? [];
        expect(sections.map((s) => s.id)).toEqual(["recent", "latest"]);
        expect(sections[0]?.items.map((i) => i.id)).toEqual(["invocations:inv2"]);
        expect(sections[1]?.items.map((i) => i.id)).toEqual(["invocations:inv1", "invocations:inv3"]);
    });

    it("fetches once and answers further keystrokes from the store", async () => {
        await invocationsProvider.searchScoped?.(SCOPE, "", makeCtx());
        expect(getInvocationsData).toHaveBeenCalledTimes(1);

        // the invocations index has no free-text search, so a query must not
        // repeat the identical unfiltered request
        await invocationsProvider.searchScoped?.(SCOPE, "r", makeCtx());
        await invocationsProvider.searchScoped?.(SCOPE, "rn", makeCtx());
        await invocationsProvider.searchScoped?.(SCOPE, "rna", makeCtx());

        expect(getInvocationsData).toHaveBeenCalledTimes(1);
    });

    it("does not refetch for a user without invocations", async () => {
        vi.mocked(getInvocationsData).mockResolvedValue([[], 0] as never);

        await invocationsProvider.searchScoped?.(SCOPE, "", makeCtx());
        await invocationsProvider.searchScoped?.(SCOPE, "rna", makeCtx());

        expect(getInvocationsData).toHaveBeenCalledTimes(1);
    });

    it("refreshes the cached list in the background once it goes stale", async () => {
        await invocationsProvider.searchScoped?.(SCOPE, "", makeCtx());
        expect(getInvocationsData).toHaveBeenCalledTimes(1);

        resetListRefreshTracking();
        const sections = (await invocationsProvider.searchScoped?.(SCOPE, "", makeCtx())) ?? [];

        expect(sections.at(-1)?.items.map((i) => i.id)).toEqual([
            "invocations:inv1",
            "invocations:inv2",
            "invocations:inv3",
        ]);
        expect(getInvocationsData).toHaveBeenCalledTimes(2);
    });

    it("keeps rendering the cached invocations when a fetch fails", async () => {
        await invocationsProvider.searchScoped?.(SCOPE, "", makeCtx());
        vi.mocked(getInvocationsData).mockRejectedValue(new Error("boom"));
        resetListRefreshTracking();

        const sections = (await invocationsProvider.searchScoped?.(SCOPE, "rna", makeCtx())) ?? [];

        expect(sections[0]?.items.map((i) => i.id)).toEqual(["invocations:inv2"]);
    });

    it("keeps the scope empty rather than failing when the first fetch fails", async () => {
        vi.mocked(getInvocationsData).mockRejectedValue(new Error("boom"));

        const sections = (await invocationsProvider.searchScoped?.(SCOPE, "", makeCtx())) ?? [];

        expect(sections).toEqual([]);
    });

    it("returns a single results section for a scoped query", async () => {
        const sections = (await invocationsProvider.searchScoped?.(SCOPE, "rna", makeCtx())) ?? [];
        expect(sections).toHaveLength(1);
        expect(sections[0]?.id).toBe("results");
        expect(sections[0]?.items.map((i) => i.id)).toEqual(["invocations:inv2"]);
    });
});
