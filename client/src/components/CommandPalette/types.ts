import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";

import type { ScopeDefinition } from "./providers/scopes";

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
    /** Turns the item into a badge collecting a second value before it runs */
    argumentMode?: {
        placeholder: string;
        getItems(argQuery: string, ctx: PaletteContext): PaletteItem[] | Promise<PaletteItem[]>;
    };
    /** Imperative action to run on selection */
    handler?: () => void;
    /** Icon shown in front of the title */
    icon?: IconDefinition;
    /** Extra search corpus, never displayed */
    keywords?: string;
    /**
     * Identity under which the palette remembers this item once it is opened
     * (see `useRecentPaletteItems`). Recorded centrally by the palette, so a
     * provider only declares it and never writes the MRU list itself.
     */
    mru?: {
        /** Entity type, e.g. "history" — one MRU bucket per type */
        type: string;
        /** Entity id, unique within its type */
        id: string;
    };
    /** Alternative run triggered with shift+enter */
    secondaryAction?: {
        label: string;
        run?: (ctx: PaletteContext) => void;
        to?: string;
    };
    /** Key hint rendered right-aligned on the row (help panel rows) */
    shortcut?: string;
    /** Secondary line under the title */
    subtitle?: string;
    title: string;
    /** Router location to navigate to on selection */
    to?: string;
}

/** A titled group of items returned by a scoped provider search */
export interface ScopedSection {
    /** Unique within the provider, e.g. "recent" */
    id: string;
    items: PaletteItem[];
    title: string;
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
    /** Legacy single-letter prefix; scoping lives in `providers/scopes.ts` */
    prefix?: string;
    search(query: string, ctx: PaletteContext): PaletteItem[] | Promise<PaletteItem[]>;
    /** Multi-section search for one of the provider's scopes */
    searchScoped?(
        scope: ScopeDefinition,
        query: string,
        ctx: PaletteContext,
    ): ScopedSection[] | Promise<ScopedSection[]>;
    /** Section heading shown above this provider's results */
    title: string;
}
