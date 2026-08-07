import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";

/**
 * Everything a provider may need to decide which items exist for the current
 * user. Passed in by the palette component so providers stay testable.
 */
export interface PaletteContext {
    /** Whether unprivileged (user-defined) tools are available */
    canUseUnprivilegedTools: boolean;
    /** Relevant subset of the Galaxy configuration */
    config: {
        interactivetools_enable?: boolean;
        llm_api_configured?: boolean;
    };
    /** Whether the current user is an admin */
    isAdmin: boolean;
    /** Whether no user is logged in */
    isAnonymous: boolean;
}

/**
 * One result row in the command palette. Exactly one of `to` or `handler`
 * should be set: `to` navigates (and supports open-in-new-tab), `handler`
 * runs an imperative action.
 */
export interface PaletteItem {
    /** Unique across providers, by convention `${providerId}:${localId}` */
    id: string;
    /** Imperative action to run on selection */
    handler?: () => void;
    /** Icon shown in front of the title */
    icon?: IconDefinition;
    /** Extra search corpus, never displayed */
    keywords?: string;
    /** Secondary line under the title */
    subtitle?: string;
    title: string;
    /** Router location to navigate to on selection */
    to?: string;
}

/**
 * A source of palette results. Sync providers (navigation, actions) filter
 * local data; async providers (tools, and per-entity searches later) may
 * call the backend.
 */
export interface CommandPaletteProvider {
    id: string;
    /** Items shown when the query is empty (recents, defaults) */
    emptyQueryItems?(ctx: PaletteContext): PaletteItem[];
    /** Single-letter query prefix (e.g. "t") scoping search to this provider */
    prefix?: string;
    search(query: string, ctx: PaletteContext): PaletteItem[] | Promise<PaletteItem[]>;
    /** Section heading shown above this provider's results */
    title: string;
}
