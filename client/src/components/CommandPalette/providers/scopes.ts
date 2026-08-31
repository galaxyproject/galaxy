import type { PaletteContext } from "../types";

/**
 * A one- or two-letter `x:` prefix that scopes the palette to a single kind of
 * entity. `providerId` names the provider serving the scope; `variant`
 * distinguishes scopes sharing one provider (own vs. shared vs. published …).
 */
export interface ScopeDefinition {
    /** Prefix typed before the colon, lowercase and unique */
    key: string;
    /** Human readable name, shown on the badge chip and in the help panel */
    label: string;
    /** Id of the provider that serves this scope */
    providerId: string;
    /** Discriminator passed to the provider for multi-scope providers */
    variant?: string;
    /** Hidden from anonymous users */
    requiresLogin?: boolean;
    /** Extra availability check against the Galaxy configuration */
    configGate?: (ctx: PaletteContext) => boolean;
}

/** Ordered scope registry — also the order of the rows in the help panel */
export const PALETTE_SCOPES: ScopeDefinition[] = [
    { key: "w", label: "My workflows", providerId: "workflows", requiresLogin: true },
    { key: "ws", label: "Shared workflows", providerId: "workflows", variant: "shared", requiresLogin: true },
    { key: "wp", label: "Public workflows", providerId: "workflows", variant: "published", requiresLogin: true },
    { key: "t", label: "Tools", providerId: "tools" },
    { key: "h", label: "My histories", providerId: "histories", requiresLogin: true },
    { key: "hs", label: "Shared histories", providerId: "histories", variant: "shared", requiresLogin: true },
    { key: "hp", label: "Public histories", providerId: "histories", variant: "published", requiresLogin: true },
    { key: "ha", label: "Archived histories", providerId: "histories", variant: "archived", requiresLogin: true },
    { key: "d", label: "Datasets", providerId: "datasets", requiresLogin: true },
    { key: "v", label: "Visualizations", providerId: "visualizations", requiresLogin: true },
    { key: "i", label: "Invocations", providerId: "invocations", requiresLogin: true },
    { key: "p", label: "My pages", providerId: "pages", requiresLogin: true },
    { key: "pp", label: "Public pages", providerId: "pages", variant: "published", requiresLogin: true },
    {
        key: "it",
        label: "Interactive tools",
        providerId: "interactiveTools",
        configGate: (ctx) => Boolean(ctx.config.interactivetools_enable),
    },
    // no `requiresLogin`: the provider already drops the rows an anonymous user
    // cannot reach, so the scope stays useful without an account
    { key: "n", label: "Navigation", providerId: "navigation" },
];

/**
 * The `>` sigil behaves like a scope but is not typed with a colon, so it
 * lives outside {@link PALETTE_SCOPES} and is matched by the parser directly.
 */
export const ACTIONS_SCOPE: ScopeDefinition = { key: ">", label: "Actions", providerId: "actions" };

/** Exact (case-insensitive) scope lookup; unknown keys are not scopes */
export function findScope(key: string): ScopeDefinition | undefined {
    const normalized = key.toLowerCase();
    return PALETTE_SCOPES.find((scope) => scope.key === normalized);
}

/**
 * Whether the instance left a provider on. Lives here rather than in
 * `providers/index.ts` because every provider imports this module, and the
 * registry imports every provider — the check has to sit below both.
 */
export function isProviderEnabled(providerId: string, ctx: PaletteContext): boolean {
    return !(ctx.config.command_palette_disabled_providers ?? []).includes(providerId);
}

/** Whether a scope may be used by the current user on this Galaxy instance */
export function isScopeAvailable(scope: ScopeDefinition, ctx: PaletteContext): boolean {
    // a scope is only a way into its provider, so a disabled one has none: this
    // covers the help panel rows, the category tabs, the `x:` tokens the machine
    // would otherwise turn into a badge, and the `>` sigil alike
    if (!isProviderEnabled(scope.providerId, ctx)) {
        return false;
    }
    if (scope.requiresLogin && ctx.isAnonymous) {
        return false;
    }
    return scope.configGate ? scope.configGate(ctx) : true;
}

/** All scopes usable by the current user, in registry order */
export function availableScopes(ctx: PaletteContext): ScopeDefinition[] {
    return PALETTE_SCOPES.filter((scope) => isScopeAvailable(scope, ctx));
}
