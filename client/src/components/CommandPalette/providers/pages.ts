import { faFileAlt } from "@fortawesome/free-solid-svg-icons";
import { format } from "date-fns";

import type { PageSummary } from "@/api/pages";
import { useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { type PageListVariant, usePageStore } from "@/stores/pageStore";
import { useUserStore } from "@/stores/userStore";
import { galaxyTimeToDate } from "@/utils/dates";

import type { CommandPaletteProvider, PaletteContext, PaletteItem, ScopedSection } from "../types";
import { rankPaletteItems } from "../utilities";
import { markListRefreshed, refreshListWhenStale } from "./refresh";
import type { ScopeDefinition } from "./scopes";

/** Entity type used for the palette's most-recently-used list */
export const PAGE_MRU_TYPE = "page";

/** Per section cap, small enough to keep the scoped view scannable */
const SECTION_LIMIT = 8;
const RECENT_LIMIT = 5;
/** Below this length an unscoped query fans out too broadly to be useful */
const MIN_ROOT_QUERY_LENGTH = 2;

/** Canonical read-only view of a page, same target the pages grids use */
export function pageDisplayPath(pageId: string): string {
    return `/published/page?id=${pageId}`;
}

/** Content editor of a page, only reachable for pages the user owns */
export function pageEditorPath(pageId: string): string {
    return `/pages/editor?id=${pageId}`;
}

function formatUpdateTime(updateTime: unknown): string {
    if (typeof updateTime !== "string" || !updateTime) {
        return "";
    }
    try {
        return format(galaxyTimeToDate(updateTime), "MMM d, yyyy");
    } catch {
        return "";
    }
}

/**
 * Whether the page editor may be offered for this row. The `p:` listing is
 * requested with `showOwn` alone, so everything it returns is the user's own;
 * every other source (the `pp:` listing, and the palette's own recents, which
 * remember pages from both scopes) may hold foreign pages and is decided by the
 * owner's username.
 */
function ownsPage(page: PageSummary, variant: PageListVariant): boolean {
    return variant === "my" || useUserStore().matchesCurrentUsername(page.username);
}

function pageToItem(page: PageSummary, variant: PageListVariant): PaletteItem {
    const item: PaletteItem = {
        id: `pages:${page.id}`,
        icon: faFileAlt,
        keywords: [page.slug, page.username].filter(Boolean).join(" "),
        mru: { type: PAGE_MRU_TYPE, id: page.id },
        subtitle: [page.slug, formatUpdateTime(page.update_time)].filter(Boolean).join(" · "),
        title: page.title,
        to: pageDisplayPath(page.id),
    };
    if (ownsPage(page, variant)) {
        item.secondaryAction = { label: "Edit content", to: pageEditorPath(page.id) };
    }
    return item;
}

function variantOf(scope: ScopeDefinition): PageListVariant {
    return scope.variant === "published" ? "published" : "my";
}

/** Store cache as palette items, most recently updated first */
function cachedItems(variant: PageListVariant): PaletteItem[] {
    const pageStore = usePageStore();
    return [...pageStore.getPages(variant)]
        .sort((a, b) => String(b.update_time ?? "").localeCompare(String(a.update_time ?? "")))
        .map((page) => pageToItem(page, variant));
}

/**
 * Renders from the store cache first and only asks the backend when the cache
 * was never filled or cannot hold enough matches; results are merged into the
 * store by `fetchPages`, so nothing is duplicated palette side.
 *
 * Completeness comes from `pageStore.isComplete`, which only trusts the total
 * reported by an unfiltered listing: a search that found nothing says nothing
 * about the rest of the list and must not silence later requests.
 *
 * @param cacheOnly never request anything, not even to fill an empty cache —
 * the unscoped root fan-out runs on every provider at once and only filters what
 * the stores already hold; the `p:`/`pp:` scopes do the fetching.
 */
async function storeFirstItems(
    variant: PageListVariant,
    query: string,
    limit: number,
    cacheOnly = false,
): Promise<PaletteItem[]> {
    const pageStore = usePageStore();
    let items = rankPaletteItems(cachedItems(variant), query);
    if (cacheOnly) {
        return items.slice(0, limit);
    }

    const needsMore = items.length < limit && !pageStore.isComplete(variant);
    if (!pageStore.isLoaded(variant) || needsMore) {
        try {
            await pageStore.fetchPages(variant, query ? { search: query, limit } : { limit: SECTION_LIMIT });
            items = rankPaletteItems(cachedItems(variant), query);
        } catch {
            // keep whatever the cache holds; the palette never blocks on errors
        }
        markListRefreshed(`pages:${variant}`);
    } else {
        refreshListWhenStale(`pages:${variant}`, () => pageStore.fetchPages(variant, { limit: SECTION_LIMIT }));
    }
    return items.slice(0, limit);
}

/** Items the user opened through the palette before, best match first */
function recentItems(query: string, limit: number): PaletteItem[] {
    const pageStore = usePageStore();
    const { recentItems: readRecentItems } = useRecentPaletteItems();
    const items = readRecentItems(PAGE_MRU_TYPE).map((recent) => {
        const page = pageStore.getPageById(recent.id);
        return page
            ? // the palette remembers pages from both scopes, so the editor is
              // offered on the owner's username rather than on the scope
              { ...pageToItem(page, "published"), to: recent.to ?? pageDisplayPath(recent.id) }
            : {
                  id: `pages:${recent.id}`,
                  icon: faFileAlt,
                  mru: { type: PAGE_MRU_TYPE, id: recent.id },
                  title: recent.name,
                  to: recent.to ?? pageDisplayPath(recent.id),
              };
    });
    return rankPaletteItems(items, query).slice(0, limit);
}

export const pagesProvider: CommandPaletteProvider = {
    id: "pages",
    title: "Pages",
    /** Root mode with no query: the pages opened through the palette before */
    emptyQueryItems(ctx: PaletteContext) {
        if (ctx.isAnonymous) {
            return [];
        }
        return recentItems("", RECENT_LIMIT);
    },
    /** Unscoped fan-out over the cached own pages, without a request */
    async search(query: string, ctx: PaletteContext) {
        const trimmed = query.trim();
        if (ctx.isAnonymous || trimmed.length < MIN_ROOT_QUERY_LENGTH) {
            return [];
        }
        return storeFirstItems("my", trimmed, RECENT_LIMIT, true);
    },
    /**
     * `p:` own pages as Recent + list sections, `pp:` the published list alone.
     * The palette remembers one list per entity type rather than per scope, so
     * the recents are offered by the base scope only — a page the user opened
     * from `p:` has no business showing up under "public".
     */
    async searchScoped(scope: ScopeDefinition, query: string, ctx: PaletteContext) {
        if (ctx.isAnonymous) {
            return [];
        }
        const variant = variantOf(scope);
        const trimmed = query.trim();
        const recent = variant === "my" ? recentItems(trimmed, RECENT_LIMIT) : [];
        const recentIds = new Set(recent.map((item) => item.id));
        const listed = (await storeFirstItems(variant, trimmed, SECTION_LIMIT + recentIds.size))
            .filter((item) => !recentIds.has(item.id))
            .slice(0, SECTION_LIMIT);

        const sections: ScopedSection[] = [];
        if (recent.length) {
            sections.push({ id: "recent", title: "Recent", items: recent });
        }
        sections.push({
            id: variant === "published" ? "published" : "latest",
            title: trimmed ? scope.label : "Latest",
            items: listed,
        });
        return sections;
    },
};
