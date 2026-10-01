/** The provider skeleton histories and workflows share: an own list with recents, plus listings per scope variant */
import type { CommandPaletteProvider, PaletteItem, ScopedSection } from "../types";
import { PALETTE_LIMITS } from "./limits";
import { recentPaletteItems, type RecentRows } from "./recent";
import { rootListItems, storeFirstItems, type StoreFirstList } from "./storeFirst";

/** The per-entity half of a listing provider; `V` names the listings, `my` is the user's own list */
export interface ListingProviderConfig<V extends string> {
    id: string;
    title: string;
    /** Scope variants with a listing of their own; any other variant reads the own list */
    variants: readonly V[];
    /** Listings the root answer searches; an anonymous visitor has no own or shared-with-me rows */
    rootListings: { anonymous: readonly V[]; signedIn: readonly V[] };
    list(variant: V | "my"): StoreFirstList;
    /** Root-answer backend search of one listing, leaving the listing its scope hydrates alone */
    searchListing(variant: V, query: string): Promise<PaletteItem[]>;
    /** How the entities the palette remembers render */
    recentRows(): RecentRows;
    /** Sections the base scope shows above its recents */
    leadingSections?(query: string): Promise<ScopedSection[]>;
}

export function defineListingProvider<V extends string>(config: ListingProviderConfig<V>): CommandPaletteProvider {
    function listVariant(variant?: string): V | "my" {
        return config.variants.find((known) => known === variant) ?? "my";
    }

    function recentItems(query: string): PaletteItem[] {
        return recentPaletteItems(config.recentRows(), query, PALETTE_LIMITS.section);
    }

    return {
        id: config.id,
        title: config.title,
        /** Root mode: entities the palette remembers, no request needed */
        emptyQueryItems(ctx) {
            return ctx.isAnonymous ? [] : recentItems("");
        },
        /** Root mode: the cached own list, and the root listings searched */
        search(query, ctx, options = {}) {
            const listings = ctx.isAnonymous ? config.rootListings.anonymous : config.rootListings.signedIn;
            const searches = listings.map((variant) => (text: string) => config.searchListing(variant, text));
            return rootListItems(query, ctx.isAnonymous ? undefined : config.list("my"), searches, options);
        },
        /**
         * The base scope shows its leading sections and the palette recents above the own list; a variant scope
         * shows its listing alone. The palette remembers one list per entity type, not per scope, so private
         * entities stay out of the shared and public scopes. The query filters every section.
         */
        async searchScoped(scope, query) {
            const variant = listVariant(scope.variant);
            const own = variant === "my";
            const [leading, results] = await Promise.all([
                own && config.leadingSections ? config.leadingSections(query) : [],
                storeFirstItems(config.list(variant), query, PALETTE_LIMITS.section),
            ]);
            const title = query ? (scope.variant ? scope.label : config.title) : "Latest";
            return [
                ...leading,
                { id: "recent", items: own ? recentItems(query) : [], title: "Recent" },
                { id: variant, items: results, title },
            ];
        },
    };
}
