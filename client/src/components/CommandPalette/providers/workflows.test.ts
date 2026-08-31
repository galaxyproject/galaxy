import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { WorkflowSummary } from "@/api/workflows";
import { loadWorkflows } from "@/api/workflows";
import type { RecentPaletteItem } from "@/composables/useRecentPaletteItems";
import { useUserStore } from "@/stores/userStore";

import type { PaletteContext } from "../types";
import { resetListRefreshTracking } from "./refresh";
import type { ScopeDefinition } from "./scopes";
import { workflowsProvider } from "./workflows";

vi.mock("@/api/workflows", () => ({
    loadWorkflows: vi.fn(),
}));

vi.mock("@/components/Workflow/workflows.services", () => ({
    getWorkflowFull: vi.fn(),
}));

let recent: RecentPaletteItem[] = [];

vi.mock("@/composables/useRecentPaletteItems", () => ({
    useRecentPaletteItems: () => ({
        recentItems: (type: string) => (type === "workflow" ? recent : []),
        addRecentItem: vi.fn(),
        clearRecentItems: vi.fn(),
    }),
}));

const OWN_SCOPE: ScopeDefinition = { key: "w", label: "My workflows", providerId: "workflows" };
const SHARED_SCOPE: ScopeDefinition = {
    key: "ws",
    label: "Shared workflows",
    providerId: "workflows",
    variant: "shared",
};
const PUBLISHED_SCOPE: ScopeDefinition = {
    key: "wp",
    label: "Public workflows",
    providerId: "workflows",
    variant: "published",
};

function workflow(id: string, name: string, owner = "me", updateTime = "2026-08-30T10:00:00"): WorkflowSummary {
    return { id, name, owner, update_time: updateTime, tags: [] } as unknown as WorkflowSummary;
}

const RNA = workflow("wf1", "RNA-seq analysis", "me", "2026-08-30T10:00:00");
const VARIANTS = workflow("wf2", "Variant calling", "me", "2026-08-31T10:00:00");
const BOOKMARKED = workflow("wf3", "Bookmarked assembly");
const SHARED = workflow("wf4", "Shared alignment", "colleague");
const PUBLISHED = workflow("wf5", "Public metagenomics", "stranger");
const REMOTE_ONLY = workflow("wf6", "Zebrafish pipeline");

interface LoadArgs {
    filterText?: string;
    showPublished?: boolean;
    showShared?: boolean;
}

function mockWorkflowsApi() {
    vi.mocked(loadWorkflows).mockImplementation(async ({ filterText = "", showPublished, showShared }: LoadArgs) => {
        const query = filterText
            .replace(/is:\w+/g, "")
            .trim()
            .toLowerCase();
        let data: WorkflowSummary[];
        if (filterText.includes("is:bookmarked")) {
            data = [BOOKMARKED];
        } else if (filterText.includes("is:shared_with_me")) {
            data = [SHARED];
        } else if (showPublished) {
            data = [PUBLISHED];
        } else {
            data = query ? [RNA, VARIANTS, REMOTE_ONLY] : [RNA, VARIANTS];
            if (showShared !== false) {
                // `show_shared` defaults to true on the backend and an
                // `undefined` value never reaches it, so anything but an
                // explicit `false` mixes shared-with-me workflows in
                data = [...data, SHARED];
            }
        }
        const matched = query ? data.filter((entry) => entry.name.toLowerCase().includes(query)) : data;
        return { data: matched, totalMatches: matched.length };
    });
}

function makeCtx(isAnonymous = false): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAdmin: false, isAnonymous };
}

function signIn(username = "me") {
    const userStore = useUserStore();
    userStore.currentUser = { id: "user-1", email: "me@example.org", username, isAnonymous: false } as never;
}

async function scopedSections(scope: ScopeDefinition, query = "") {
    return (await workflowsProvider.searchScoped?.(scope, query, makeCtx())) ?? [];
}

describe("workflowsProvider", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        recent = [];
        vi.mocked(loadWorkflows).mockReset();
        resetListRefreshTracking();
        mockWorkflowsApi();
        signIn();
    });

    it("shows bookmarked, recent and latest sections for an empty `w:` query", async () => {
        recent = [{ type: "workflow", id: "wf1", name: "RNA-seq analysis", to: "/workflows/run?id=wf1" }];

        const sections = await scopedSections(OWN_SCOPE);

        expect(sections.map((s) => s.title)).toEqual(["Bookmarked", "Recent", "Latest"]);
        expect(sections[0]?.items.map((i) => i.title)).toEqual(["Bookmarked assembly"]);
        expect(sections[1]?.items.map((i) => i.title)).toEqual(["RNA-seq analysis"]);
        // latest first, so the newer "Variant calling" leads
        expect(sections[2]?.items.map((i) => i.title)).toEqual(["Variant calling", "RNA-seq analysis"]);
    });

    it("runs a workflow on enter and offers the editor for owned workflows", async () => {
        const [item] = (await scopedSections(OWN_SCOPE)).at(-1)?.items ?? [];

        expect(item?.to).toBe("/workflows/run?id=wf2");
        expect(item?.secondaryAction).toEqual({ label: "Edit workflow", to: "/workflows/edit?id=wf2" });
        expect(item?.subtitle).toContain("updated");
        // the owner is redundant on the user's own workflows
        expect(item?.subtitle).not.toContain("by me");
    });

    it("names the owner and hides the editor for workflows of other users", async () => {
        const sections = await scopedSections(PUBLISHED_SCOPE);
        const [item] = sections.at(-1)?.items ?? [];

        expect(sections.map((s) => s.title)).toEqual(["Latest"]);
        expect(item?.title).toBe("Public metagenomics");
        expect(item?.subtitle).toContain("by stranger");
        expect(item?.secondaryAction).toBeUndefined();
    });

    it("keeps workflows shared with the user out of the own and bookmarked lists", async () => {
        const sections = await scopedSections(OWN_SCOPE);

        const ownRequests = vi
            .mocked(loadWorkflows)
            .mock.calls.filter(([args]) => !args.filterText?.includes("is:shared_with_me"));
        expect(ownRequests.length).toBeGreaterThan(0);
        ownRequests.forEach(([args]) => expect(args.showShared).toBe(false));
        expect(sections.flatMap((s) => s.items.map((i) => i.title))).not.toContain("Shared alignment");
    });

    it("reads the shared list for the `ws:` scope", async () => {
        const sections = await scopedSections(SHARED_SCOPE, "alignment");

        expect(sections.map((s) => s.title)).toEqual(["Shared workflows"]);
        expect(sections[0]?.items.map((i) => i.title)).toEqual(["Shared alignment"]);
        expect(vi.mocked(loadWorkflows).mock.calls.some(([args]) => args.showShared)).toBe(true);
    });

    it("filters a complete cache without querying the backend again", async () => {
        await scopedSections(OWN_SCOPE);
        const callsAfterHydration = vi.mocked(loadWorkflows).mock.calls.length;

        const sections = await scopedSections(OWN_SCOPE, "variant");

        expect(sections.at(-1)?.items.map((i) => i.title)).toEqual(["Variant calling"]);
        // "Workflows" replaces "Latest" once a query narrows the section
        expect(sections.at(-1)?.title).toBe("Workflows");
        expect(vi.mocked(loadWorkflows).mock.calls.length).toBe(callsAfterHydration);
    });

    it("refreshes a cached list in the background once the palette reopens later", async () => {
        await scopedSections(OWN_SCOPE);
        const callsAfterHydration = vi.mocked(loadWorkflows).mock.calls.length;

        // a later palette session, past the refresh interval
        resetListRefreshTracking();
        const sections = await scopedSections(OWN_SCOPE);

        expect(sections.at(-1)?.items.map((i) => i.title)).toEqual(["Variant calling", "RNA-seq analysis"]);
        // one refresh per cached list the scope renders (bookmarked and my)
        expect(vi.mocked(loadWorkflows).mock.calls.length).toBe(callsAfterHydration + 2);
    });

    it("queries the backend and merges the extra matches when the cache is a full page", async () => {
        // a full page means the backend has more workflows than the cache holds
        const page = Array.from({ length: 25 }, (_, index) => workflow(`filler-${index}`, `Filler ${index}`));
        vi.mocked(loadWorkflows).mockImplementation(async ({ filterText = "" }: LoadArgs) => {
            if (filterText.includes("is:bookmarked")) {
                return { data: [], totalMatches: 0 };
            }
            const data = filterText ? [REMOTE_ONLY] : page;
            return { data, totalMatches: data.length };
        });

        const sections = await scopedSections(OWN_SCOPE, "zebrafish");

        expect(sections.at(-1)?.items.map((i) => i.title)).toEqual(["Zebrafish pipeline"]);
        expect(vi.mocked(loadWorkflows).mock.calls.some(([args]) => args.filterText === "zebrafish")).toBe(true);
    });

    it("drops backend rows the query does not match", async () => {
        // a full page keeps the cache incomplete, so the query reaches the
        // backend — which answers a short search with everything it has
        const page = Array.from({ length: 25 }, (_, index) => workflow(`filler-${index}`, `Filler ${index}`));
        vi.mocked(loadWorkflows).mockImplementation(async ({ filterText = "" }: LoadArgs) => {
            if (filterText.includes("is:bookmarked")) {
                return { data: [], totalMatches: 0 };
            }
            return { data: page, totalMatches: page.length };
        });

        const sections = await scopedSections(OWN_SCOPE, "zqx");

        expect(vi.mocked(loadWorkflows).mock.calls.some(([args]) => args.filterText === "zqx")).toBe(true);
        expect(sections.flatMap((s) => s.items)).toEqual([]);
    });

    it("keeps the same workflow addressable in several sections", async () => {
        recent = [{ type: "workflow", id: "wf2", name: "Variant calling" }];

        const sections = await scopedSections(OWN_SCOPE);
        const ids = sections.flatMap((s) => s.items.map((i) => i.id));

        expect(new Set(ids).size).toBe(ids.length);
        expect(ids).toContain("workflows:recent:wf2");
        expect(ids).toContain("workflows:my:wf2");
    });

    it("falls back to the remembered name for workflows missing from the store", async () => {
        recent = [{ type: "workflow", id: "wf9", name: "Forgotten workflow" }];

        const sections = await scopedSections(OWN_SCOPE);
        const [item] = sections.find((s) => s.id === "recent")?.items ?? [];

        expect(item?.title).toBe("Forgotten workflow");
        expect(item?.to).toBe("/workflows/run?id=wf9");
    });

    it("keeps the palette recents out of the shared and published scopes", async () => {
        // the MRU is one list per entity type, so a private workflow opened
        // through `w:` must not leak into the shared or published scopes
        recent = [{ type: "workflow", id: "wf2", name: "Variant calling" }];

        const shared = await scopedSections(SHARED_SCOPE);
        const published = await scopedSections(PUBLISHED_SCOPE);

        expect(shared.map((s) => s.id)).not.toContain("recent");
        expect(published.map((s) => s.id)).not.toContain("recent");
        expect(shared.flatMap((s) => s.items.map((i) => i.title))).not.toContain("Variant calling");
        expect(published.flatMap((s) => s.items.map((i) => i.title))).not.toContain("Variant calling");
        // the base scope still offers them
        expect((await scopedSections(OWN_SCOPE)).map((s) => s.id)).toContain("recent");
    });

    it("stays out of the unscoped fan-out for short queries and anonymous users", async () => {
        expect(await workflowsProvider.search("v", makeCtx())).toEqual([]);
        expect(await workflowsProvider.search("variant", makeCtx(true))).toEqual([]);
        expect(loadWorkflows).not.toHaveBeenCalled();
    });

    it("filters the cached list in the unscoped fan-out and never fetches there", async () => {
        // nothing cached yet: the fan-out contributes nothing rather than fetching
        expect(await workflowsProvider.search("variant", makeCtx())).toEqual([]);
        expect(loadWorkflows).not.toHaveBeenCalled();

        await scopedSections(OWN_SCOPE);
        const callsAfterHydration = vi.mocked(loadWorkflows).mock.calls.length;

        const items = await workflowsProvider.search("variant", makeCtx());

        expect(items.map((i) => i.title)).toEqual(["Variant calling"]);
        expect(vi.mocked(loadWorkflows).mock.calls.length).toBe(callsAfterHydration);
    });

    it("lists remembered workflows for an empty root query", async () => {
        recent = [{ type: "workflow", id: "wf1", name: "RNA-seq analysis" }];

        expect(workflowsProvider.emptyQueryItems?.(makeCtx())?.map((i) => i.title)).toEqual(["RNA-seq analysis"]);
        expect(workflowsProvider.emptyQueryItems?.(makeCtx(true))).toEqual([]);
    });
});
