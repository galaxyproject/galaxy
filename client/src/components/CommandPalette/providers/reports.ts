import { faFileAlt } from "@fortawesome/free-solid-svg-icons";

import type { PageSummary } from "@/api/pages";
import { type PageListVariant, usePageStore } from "@/stores/pageStore";
import { useUserStore } from "@/stores/userStore";
import { shortDateLabel } from "@/utils/dates";

import type {
    CommandPaletteProvider,
    PaletteContext,
    PaletteItem,
    PaletteSearchOptions,
    ScopedSection,
} from "../types";
import { PALETTE_LIMITS } from "./limits";
import { recentPaletteItems, type RecentRows } from "./recent";
import type { ScopeDefinition } from "./scopes";
import { rootListItems, storeFirstItems, type StoreFirstList } from "./storeFirst";

/** Entity type used for the palette's most-recently-used list */
export const PAGE_MRU_TYPE = "page";

/** Canonical read-only view of a page, same target the pages grids use */
export function pageDisplayPath(pageId: string): string {
    return `/published/page?id=${pageId}`;
}

/** Content editor of a page, only reachable for pages the user owns */
export function pageEditorPath(pageId: string): string {
    return `/pages/editor?id=${pageId}`;
}

/**
 * Whether the page editor may be offered for this row. The `r:` listing is
 * requested with `showOwn` alone, so everything it returns is the user's own;
 * every other source (the `rp:` listing, and the palette's own recents, which
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
        subtitle: [page.slug, shortDateLabel(page.update_time)].filter(Boolean).join(" · "),
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
function cachedRows(variant: PageListVariant): PaletteItem[] {
    const pageStore = usePageStore();
    return [...pageStore.getPages(variant)]
        .sort((a, b) => String(b.update_time ?? "").localeCompare(String(a.update_time ?? "")))
        .map((page) => pageToItem(page, variant));
}

/**
 * One page list, store first. Completeness comes from `pageStore.isComplete`,
 * which only trusts the total an unfiltered listing reported: a search that found
 * nothing says nothing about the rest of the list and must not silence later
 * requests.
 */
function reportList(variant: PageListVariant): StoreFirstList {
    const pageStore = usePageStore();
    return {
        key: `reports:${variant}`,
        isLoaded: () => pageStore.isLoaded(variant),
        fetchListing: () => pageStore.fetchPages(variant, { limit: PALETTE_LIMITS.page }),
        cachedItems: () => cachedRows(variant),
        isComplete: () => pageStore.isComplete(variant),
        async searchItems(query) {
            // merged into the listing by `fetchPages`, which the cache read picks up
            await pageStore.fetchPages(variant, { search: query, limit: PALETTE_LIMITS.page });
            return [];
        },
    };
}

/**
 * The root answer's search of the published pages: its matches alone, which are
 * not the listing, so `record: false` keeps them out of it — `rp:` still finds
 * its listing unfetched and fetches it itself.
 */
async function publishedSearch(query: string): Promise<PaletteItem[]> {
    const pages = await usePageStore().fetchPages("published", {
        search: query,
        limit: PALETTE_LIMITS.page,
        record: false,
    });
    return pages.map((page) => pageToItem(page, "published"));
}

/** Items the user opened through the palette before, best match first */
function recentItems(query: string, limit: number): PaletteItem[] {
    const pageStore = usePageStore();
    const rows: RecentRows = {
        type: PAGE_MRU_TYPE,
        stored: (entry) => {
            const page = pageStore.getPageById(entry.id);
            // the palette remembers pages from both scopes, so the editor is
            // offered on the owner's username rather than on the scope
            return page ? { ...pageToItem(page, "published"), to: entry.to ?? pageDisplayPath(entry.id) } : undefined;
        },
        fallback: (entry) => ({ id: `pages:${entry.id}`, icon: faFileAlt, to: pageDisplayPath(entry.id) }),
    };
    return recentPaletteItems(rows, query, limit);
}

export const reportsProvider: CommandPaletteProvider = {
    id: "reports",
    title: "Reports",
    /** Root mode with no query: the pages opened through the palette before */
    emptyQueryItems(ctx: PaletteContext) {
        if (ctx.isAnonymous) {
            return [];
        }
        return recentItems("", PALETTE_LIMITS.recent);
    },
    /** Root mode: the cached own pages, and the published ones searched */
    search(query: string, ctx: PaletteContext, options: PaletteSearchOptions = {}) {
        // an anonymous visitor has no own pages, so the public ones are the whole answer
        const own = ctx.isAnonymous ? undefined : reportList("my");
        return rootListItems(query, own, [publishedSearch], options);
    },
    /**
     * `r:` own pages as Recent + list sections, `rp:` the published list alone.
     * The palette remembers one list per entity type rather than per scope, so
     * the recents are offered by the base scope only — a page the user opened
     * from `r:` has no business showing up under "public".
     *
     * Published pages are public, so `rp:` serves anonymous visitors too; only
     * the own listing needs an account to hold anything.
     */
    async searchScoped(scope: ScopeDefinition, query: string, ctx: PaletteContext) {
        const variant = variantOf(scope);
        if (ctx.isAnonymous && variant === "my") {
            return [];
        }
        const recent = variant === "my" ? recentItems(query, PALETTE_LIMITS.recent) : [];
        const recentIds = new Set(recent.map((item) => item.id));
        const listed = (await storeFirstItems(reportList(variant), query, PALETTE_LIMITS.section + recentIds.size))
            .filter((item) => !recentIds.has(item.id))
            .slice(0, PALETTE_LIMITS.section);

        const sections: ScopedSection[] = [];
        if (recent.length) {
            sections.push({ id: "recent", title: "Recent", items: recent });
        }
        sections.push({
            id: variant === "published" ? "published" : "latest",
            title: query ? scope.label : "Latest",
            items: listed,
        });
        return sections;
    },
};
