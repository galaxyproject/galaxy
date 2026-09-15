import { faSitemap } from "@fortawesome/free-solid-svg-icons";
import { format } from "date-fns";

import type { WorkflowInvocation } from "@/api/invocations";
import { useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { useHistoryStore } from "@/stores/historyStore";
import { useInvocationStore } from "@/stores/invocationStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { galaxyTimeToDate } from "@/utils/dates";

import type { CommandPaletteProvider, PaletteItem, ScopedSection } from "../types";
import { rankPaletteItems } from "../utilities";
import { markListRefreshed, refreshListWhenStale } from "./refresh";
import type { ScopeDefinition } from "./scopes";

/** MRU entity type recorded for invocations opened through the palette */
export const INVOCATION_RECENT_TYPE = "invocation";

/** How many invocations are pulled into the store on scope entry */
const LATEST_LIMIT = 15;

/** Identity of the cached list in the palette's refresh bookkeeping */
const REFRESH_KEY = "invocations:latest";

/** Maximum rows rendered per section */
const SECTION_CAP = 8;

function invocationRoute(invocationId: string): string {
    return `/workflows/invocations/${invocationId}`;
}

function formatCreateTime(createTime: string | null | undefined): string | undefined {
    if (!createTime) {
        return undefined;
    }
    try {
        return format(galaxyTimeToDate(createTime), "MMM d, yyyy");
    } catch {
        return undefined;
    }
}

/**
 * Names come from the history and workflow stores, which `fetchLatestInvocations`
 * populates (and awaits) before it resolves -- never fetched here, so rendering a
 * row never triggers a request.
 */
function invocationNames(invocation: WorkflowInvocation) {
    const historyStore = useHistoryStore();
    const workflowStore = useWorkflowStore();
    const workflowName = workflowStore.getStoredWorkflowNameByInstanceId(invocation.workflow_id, "");
    const historyName = historyStore.getHistoryById(invocation.history_id, false)?.name;
    return { workflowName, historyName };
}

function invocationToItem(invocation: WorkflowInvocation): PaletteItem {
    const { workflowName, historyName } = invocationNames(invocation);
    const subtitle = [invocation.state, formatCreateTime(invocation.create_time), historyName]
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
            await invocationStore.fetchLatestInvocations(LATEST_LIMIT);
        } catch (error) {
            console.debug("Command palette could not fetch invocations", error);
        }
        markListRefreshed(REFRESH_KEY);
    } else {
        refreshListWhenStale(REFRESH_KEY, () => invocationStore.fetchLatestInvocations(LATEST_LIMIT));
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
    const { recentItems } = useRecentPaletteItems();
    return recentItems(INVOCATION_RECENT_TYPE).map((recent) => {
        const invocation = invocationStore.latestInvocations.find(
            (candidate: WorkflowInvocation) => candidate.id === recent.id,
        );
        if (invocation) {
            return invocationToItem(invocation);
        }
        return {
            id: `invocations:${recent.id}`,
            icon: faSitemap,
            mru: { type: INVOCATION_RECENT_TYPE, id: recent.id },
            title: recent.name || `Invocation ${recent.id}`,
            to: recent.to ?? invocationRoute(recent.id),
        };
    });
}

function section(id: string, title: string, items: PaletteItem[]): ScopedSection[] {
    return items.length ? [{ id, items: items.slice(0, SECTION_CAP), title }] : [];
}

export const invocationsProvider: CommandPaletteProvider = {
    id: "invocations",
    title: "Invocations",
    /** Whatever the store already knows, newest first -- never fetches */
    emptyQueryItems() {
        const invocationStore = useInvocationStore();
        return invocationStore.latestInvocations.slice(0, SECTION_CAP).map(invocationToItem);
    },
    /**
     * Root mode fan-out: the unscoped palette asks every provider at once, so
     * this only filters what the store already holds. The `i:` scope is the one
     * that fetches.
     */
    search(query: string) {
        const trimmed = query.trim();
        if (!trimmed) {
            return [];
        }
        return filterInvocations(useInvocationStore().latestInvocations, trimmed).slice(0, SECTION_CAP);
    },
    async searchScoped(_scope: ScopeDefinition, query: string): Promise<ScopedSection[]> {
        const trimmed = query.trim();
        const invocations = await ensureLatestInvocations();
        if (!trimmed) {
            // "Latest" keeps the server's order (most recently created first) and drops
            // whatever the "Recent" section already shows.
            const recent = recentInvocationItems();
            const recentIds = new Set(recent.map((item) => item.id));
            const latest = invocations.map(invocationToItem).filter((item) => !recentIds.has(item.id));
            return [...section("recent", "Recent", recent), ...section("latest", "Latest", latest)];
        }
        return section("results", "Invocations", filterInvocations(invocations, trimmed));
    },
};
