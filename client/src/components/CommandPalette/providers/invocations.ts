import { faSitemap } from "@fortawesome/free-solid-svg-icons";

import type { WorkflowInvocation } from "@/api/invocations";
import { useHistoryStore } from "@/stores/historyStore";
import { useInvocationStore } from "@/stores/invocationStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { shortDateLabel } from "@/utils/dates";

import type { CommandPaletteProvider, PaletteItem, ScopedSection } from "../types";
import { PALETTE_LIMITS } from "./limits";
import { recentPaletteItems, type RecentRows } from "./recent";
import type { ScopeDefinition } from "./scopes";
import { ensureListHydrated, storeFirstItems, type StoreFirstList } from "./storeFirst";

/** MRU entity type recorded for invocations opened through the palette */
export const INVOCATION_RECENT_TYPE = "invocation";

/** How many invocations are pulled into the store on scope entry */
const LATEST_LIMIT = 15;

function invocationRoute(invocationId: string): string {
    return `/workflows/invocations/${invocationId}`;
}

/** Names are read from the stores only, so rendering a row never triggers a request */
function invocationNames(invocation: WorkflowInvocation) {
    const historyStore = useHistoryStore();
    const workflowStore = useWorkflowStore();
    const workflowName = workflowStore.getStoredWorkflowNameByInstanceId(invocation.workflow_id, "");
    const historyName = historyStore.getHistoryById(invocation.history_id, false)?.name;
    return { workflowName, historyName };
}

function invocationToItem(invocation: WorkflowInvocation): PaletteItem {
    const { workflowName, historyName } = invocationNames(invocation);
    const subtitle = [invocation.state, shortDateLabel(invocation.create_time), historyName]
        .filter(Boolean)
        .join(" · ");
    return {
        id: `invocations:${invocation.id}`,
        icon: faSitemap,
        keywords: [historyName, invocation.id].filter(Boolean).join(" "),
        mru: { type: INVOCATION_RECENT_TYPE, id: invocation.id },
        subtitle: subtitle || undefined,
        title: workflowName || `Invocation ${invocation.id}`,
        to: invocationRoute(invocation.id),
    };
}

/** Awaits the name lookups `getData` only starts, so fresh rows show names; a failed lookup only costs a name */
async function fetchInvocationNames(invocations: WorkflowInvocation[]): Promise<void> {
    const historyStore = useHistoryStore();
    const workflowStore = useWorkflowStore();
    const historyIds = new Set(invocations.map((invocation) => invocation.history_id).filter(Boolean));
    const workflowIds = new Set(invocations.map((invocation) => invocation.workflow_id).filter(Boolean));
    await Promise.all([
        ...[...historyIds].map((historyId) =>
            historyStore.getHistoryById(historyId, false)
                ? Promise.resolve()
                : historyStore.loadHistoryById(historyId).catch(() => undefined),
        ),
        ...[...workflowIds].map((workflowId) =>
            workflowStore.fetchWorkflowForInstanceIdCached(workflowId).catch(() => undefined),
        ),
    ]);
}

/** The latest invocations, settling once the names their rows show are known too */
async function fetchLatestInvocationsWithNames(): Promise<void> {
    const invocations = await useInvocationStore().fetchLatestInvocations(LATEST_LIMIT);
    await fetchInvocationNames(invocations);
}

/** The latest invocations, store first; the index has no free-text search, so no `searchItems` and the cache answers */
function invocationList(): StoreFirstList {
    const invocationStore = useInvocationStore();
    return {
        key: "invocations:latest",
        isLoaded: () => invocationStore.hasLoadedLatestInvocations,
        fetchListing: fetchLatestInvocationsWithNames,
        cachedItems: () => invocationStore.latestInvocations.map(invocationToItem),
        // a page of the latest knows no total; never read, as there is no backend search
        isComplete: () => false,
    };
}

/** Remembered invocations, refreshed against the store cache when it knows them */
function recentInvocationItems(): PaletteItem[] {
    const invocationStore = useInvocationStore();
    const rows: RecentRows = {
        type: INVOCATION_RECENT_TYPE,
        stored: (entry) => {
            const invocation = invocationStore.latestInvocations.find((candidate) => candidate.id === entry.id);
            return invocation ? invocationToItem(invocation) : undefined;
        },
        fallback: (entry) => ({
            id: `invocations:${entry.id}`,
            icon: faSitemap,
            title: entry.name || `Invocation ${entry.id}`,
            to: invocationRoute(entry.id),
        }),
    };
    return recentPaletteItems(rows, "", PALETTE_LIMITS.section);
}

export const invocationsProvider: CommandPaletteProvider = {
    id: "invocations",
    title: "Invocations",
    /** Whatever the store already knows, newest first -- never fetches */
    emptyQueryItems() {
        const invocationStore = useInvocationStore();
        return invocationStore.latestInvocations.slice(0, PALETTE_LIMITS.section).map(invocationToItem);
    },
    /**
     * Root mode fan-out: this provider only filters what the store already
     * holds, unlike the histories, workflows, reports and tools ones, which
     * search the backend there too. The `i:` scope is the one that fetches.
     */
    async search(query: string) {
        if (!query) {
            return [];
        }
        return storeFirstItems(invocationList(), query, PALETTE_LIMITS.section, { cacheOnly: true });
    },
    async searchScoped(_scope: ScopeDefinition, query: string): Promise<ScopedSection[]> {
        const list = invocationList();
        if (!query) {
            await ensureListHydrated(list);
            // "Latest" keeps the server's order (most recently created first) and drops
            // whatever the "Recent" section already shows.
            const recent = recentInvocationItems();
            const recentIds = new Set(recent.map((item) => item.id));
            const latest = list.cachedItems().filter((item) => !recentIds.has(item.id));
            return [
                { id: "recent", items: recent, title: "Recent" },
                { id: "latest", items: latest.slice(0, PALETTE_LIMITS.section), title: "Latest" },
            ];
        }
        return [
            { id: "results", items: await storeFirstItems(list, query, PALETTE_LIMITS.section), title: "Invocations" },
        ];
    },
};
