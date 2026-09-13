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

/**
 * Ordered scope registry — also the order of the rows in the help panel.
 *
 * The `wp:`, `hp:` and `rp:` scopes carry no `requiresLogin`: published entities
 * are public, and their listings are exactly what an anonymous visitor may
 * browse. Everything an account owns — the own and shared-with-me scopes
 * included — stays behind a login.
 */
export const PALETTE_SCOPES: ScopeDefinition[] = [
    { key: "w", label: "My workflows", providerId: "workflows", requiresLogin: true },
    { key: "ws", label: "Shared workflows", providerId: "workflows", variant: "shared", requiresLogin: true },
    { key: "wp", label: "Public workflows", providerId: "workflows", variant: "published" },
    { key: "t", label: "Tools", providerId: "tools" },
    { key: "h", label: "My histories", providerId: "histories", requiresLogin: true },
    { key: "hs", label: "Shared histories", providerId: "histories", variant: "shared", requiresLogin: true },
    { key: "hp", label: "Public histories", providerId: "histories", variant: "published" },
    { key: "ha", label: "Archived histories", providerId: "histories", variant: "archived", requiresLogin: true },
    { key: "d", label: "Datasets", providerId: "datasets", requiresLogin: true },
    { key: "v", label: "Visualizations", providerId: "visualizations", requiresLogin: true },
    { key: "i", label: "Invocations", providerId: "invocations", requiresLogin: true },
    { key: "r", label: "My reports", providerId: "reports", requiresLogin: true },
    { key: "rp", label: "Public reports", providerId: "reports", variant: "published" },
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

/**
 * Whether an account is the only thing between the current user and a scope.
 * A provider the instance turned off — or a scope whose own config gate is
 * unmet — does not exist on this Galaxy at all, so it stays hidden rather than
 * asking for a login that would not unlock it either.
 */
export function isScopeLoginGated(scope: ScopeDefinition, ctx: PaletteContext): boolean {
    if (!scope.requiresLogin || !ctx.isAnonymous || !isProviderEnabled(scope.providerId, ctx)) {
        return false;
    }
    return scope.configGate ? scope.configGate(ctx) : true;
}

/** The scopes logging in would add, in registry order — empty for a known user */
export function loginGatedScopes(ctx: PaletteContext): ScopeDefinition[] {
    return PALETTE_SCOPES.filter((scope) => isScopeLoginGated(scope, ctx));
}
