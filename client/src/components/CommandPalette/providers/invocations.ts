import { faSitemap } from "@fortawesome/free-solid-svg-icons";

import type { WorkflowInvocation } from "@/api/invocations";
import { useHistoryStore } from "@/stores/historyStore";
import { useInvocationStore } from "@/stores/invocationStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { shortDateLabel } from "@/utils/dates";

import type { CommandPaletteProvider, PaletteItem, ScopedSection } from "../types";
import { rankPaletteItems } from "../utilities";
import { PALETTE_LIMITS } from "./limits";
import { recentPaletteItems, type RecentRows } from "./recent";
import { markListRefreshed, refreshListWhenStale } from "./refresh";
import type { ScopeDefinition } from "./scopes";

/** MRU entity type recorded for invocations opened through the palette */
export const INVOCATION_RECENT_TYPE = "invocation";

/** How many invocations are pulled into the store on scope entry */
const LATEST_LIMIT = 15;

/** Identity of the cached list in the palette's refresh bookkeeping */
const REFRESH_KEY = "invocations:latest";

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

/**
 * Store-first hydration: the store is filled once per session and every later
 * keystroke is answered from it. The invocations index has no free-text search,
 * so refetching for a query would only repeat the identical unfiltered request;
 * the list is instead refreshed in the background once it goes stale.
 *
 * A failing fetch degrades to whatever the store holds rather than emptying the
 * scope.
 */
async function ensureLatestInvocations(): Promise<WorkflowInvocation[]> {
    const invocationStore = useInvocationStore();
    if (!invocationStore.hasLoadedLatestInvocations) {
        try {
            await fetchLatestInvocationsWithNames();
        } catch (error) {
            console.debug("Command palette could not fetch invocations", error);
        }
        markListRefreshed(REFRESH_KEY);
    } else {
        refreshListWhenStale(REFRESH_KEY, fetchLatestInvocationsWithNames);
    }
    return invocationStore.latestInvocations;
}

/** Client-side filter -- the invocations index has no free-text search (v1 limitation) */
function filterInvocations(invocations: WorkflowInvocation[], query: string): PaletteItem[] {
    const items = invocations.map(invocationToItem);
    return rankPaletteItems(items, query);
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

function section(id: string, title: string, items: PaletteItem[]): ScopedSection[] {
    return items.length ? [{ id, items: items.slice(0, PALETTE_LIMITS.section), title }] : [];
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
    search(query: string) {
        if (!query) {
            return [];
        }
        return filterInvocations(useInvocationStore().latestInvocations, query).slice(0, PALETTE_LIMITS.section);
    },
    async searchScoped(_scope: ScopeDefinition, query: string): Promise<ScopedSection[]> {
        const invocations = await ensureLatestInvocations();
        if (!query) {
            // "Latest" keeps the server's order (most recently created first) and drops
            // whatever the "Recent" section already shows.
            const recent = recentInvocationItems();
            const recentIds = new Set(recent.map((item) => item.id));
            const latest = invocations.map(invocationToItem).filter((item) => !recentIds.has(item.id));
            return [...section("recent", "Recent", recent), ...section("latest", "Latest", latest)];
        }
        return section("results", "Invocations", filterInvocations(invocations, query));
    },
};
