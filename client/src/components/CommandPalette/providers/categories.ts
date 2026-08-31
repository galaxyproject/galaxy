import type { PaletteContext } from "../types";
import { findScope, isProviderEnabled, isScopeAvailable, type ScopeDefinition } from "./scopes";

/**
 * One entry of the root mode category row. Every category but "All" narrows the
 * results down to a single provider; `scopeKey` names the scope it borrows for
 * that — both to decide whether the category may be offered at all and to reuse
 * the provider's scoped search once it is active.
 */
export interface PaletteCategory {
    /** Unique, also the suffix of the row's `data-description` */
    id: string;
    /** Label rendered on the tab */
    label: string;
    /** Provider whose results are shown; unset for {@link ALL_CATEGORY} */
    providerId?: string;
    /** Scope reused to run the narrowed search, see {@link categoryScope} */
    scopeKey?: string;
}

/** The default: every provider fans out, nothing is filtered away */
export const ALL_CATEGORY: PaletteCategory = { id: "all", label: "All" };

/**
 * Ordered registry — also the left to right order of the category row. Actions
 * have no category of their own: they are cheap, always local and only ever
 * shown as part of "All", the `>` scope covers searching them on purpose.
 */
export const PALETTE_CATEGORIES: PaletteCategory[] = [
    { id: "workflows", label: "Workflows", providerId: "workflows", scopeKey: "w" },
    { id: "histories", label: "Histories", providerId: "histories", scopeKey: "h" },
    { id: "datasets", label: "Datasets", providerId: "datasets", scopeKey: "d" },
    { id: "visualizations", label: "Visualizations", providerId: "visualizations", scopeKey: "v" },
    { id: "invocations", label: "Invocations", providerId: "invocations", scopeKey: "i" },
    { id: "pages", label: "Pages", providerId: "pages", scopeKey: "p" },
    { id: "tools", label: "Tools", providerId: "tools", scopeKey: "t" },
    { id: "navigation", label: "Navigation", providerId: "navigation" },
];

/** Scope a category runs its narrowed search through, if it has one */
export function categoryScope(category: PaletteCategory): ScopeDefinition | undefined {
    return category.scopeKey ? findScope(category.scopeKey) : undefined;
}

/**
 * The categories usable by the current user, "All" first. A category backed by
 * a scope inherits that scope's gating, so an anonymous user is not offered a
 * filter that can never hold anything. One without a scope only has its
 * provider to answer for it.
 */
export function availableCategories(ctx: PaletteContext): PaletteCategory[] {
    const usable = PALETTE_CATEGORIES.filter((category) => {
        const scope = categoryScope(category);
        if (scope) {
            return isScopeAvailable(scope, ctx);
        }
        return category.providerId ? isProviderEnabled(category.providerId, ctx) : true;
    });
    return [ALL_CATEGORY, ...usable];
}
