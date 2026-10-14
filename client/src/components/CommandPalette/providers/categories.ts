import type { PaletteContext } from "../types";
import { findScope, isScopeAvailable, type ScopeDefinition } from "./scopes";

/** A root-row tab; all but "All" narrow to one provider through the scope they borrow */
export interface PaletteCategory {
    /** Unique, also the suffix of the row's `data-description` */
    id: string;
    /** Label rendered on the tab */
    label: string;
    /** Scope the narrowed search runs through; its provider is the category's, unset for {@link ALL_CATEGORY} */
    scope?: ScopeDefinition;
}

/** The default: every provider fans out, nothing is filtered away */
export const ALL_CATEGORY: PaletteCategory = { id: "all", label: "All" };

/**
 * Ordered registry — also the left to right order of the category row. Actions
 * have no category of their own: they are cheap, always local and only ever
 * shown as part of "All", the `>` scope covers searching them on purpose.
 */
export const PALETTE_CATEGORIES: PaletteCategory[] = [
    { id: "workflows", label: "Workflows", scope: findScope("w") },
    { id: "histories", label: "Histories", scope: findScope("h") },
    { id: "datasets", label: "Datasets", scope: findScope("d") },
    { id: "visualizations", label: "Visualizations", scope: findScope("v") },
    { id: "invocations", label: "Invocations", scope: findScope("i") },
    { id: "reports", label: "Reports", scope: findScope("r") },
    { id: "tools", label: "Tools", scope: findScope("t") },
    { id: "navigation", label: "Navigation", scope: findScope("n") },
];

/** Provider a category narrows the results to, unset for {@link ALL_CATEGORY} */
export function categoryProviderId(category: PaletteCategory): string | undefined {
    return category.scope?.providerId;
}

/**
 * The categories usable by the current user, "All" first. Every category borrows
 * a scope and inherits that scope's gating, so an anonymous user is not offered
 * a filter that can never hold anything and a provider the instance turned off
 * takes its category with it.
 */
export function availableCategories(ctx: PaletteContext): PaletteCategory[] {
    const usable = PALETTE_CATEGORIES.filter((category) =>
        category.scope ? isScopeAvailable(category.scope, ctx) : false,
    );
    return [ALL_CATEGORY, ...usable];
}
