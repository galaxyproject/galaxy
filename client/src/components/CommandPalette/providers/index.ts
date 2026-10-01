import type { CommandPaletteProvider, PaletteContext } from "../types";
import { type ParsedPaletteQuery, parsePaletteQuery, rankPaletteItems } from "../utilities";
import { actionsProvider } from "./actions";
import { datasetsProvider } from "./datasets";
import { historiesProvider } from "./histories";
import { interactiveToolsProvider } from "./interactiveTools";
import { invocationsProvider } from "./invocations";
import { navigationProvider } from "./navigation";
import { reportsProvider } from "./reports";
import { isProviderAvailable } from "./scopes";
import { toolsProvider } from "./tools";
import { visualizationsProvider } from "./visualizations";
import { workflowsProvider } from "./workflows";

/**
 * Ordered provider registry — the fallback order of the unscoped sections, and
 * the order the `providerId` of a scope is resolved in. What the user can do
 * without data comes first (actions, navigation), then the always cached tools,
 * then the entity providers in the order their scopes are listed in
 * `providers/scopes.ts`.
 */
export const paletteProviders: CommandPaletteProvider[] = [
    actionsProvider,
    navigationProvider,
    toolsProvider,
    workflowsProvider,
    historiesProvider,
    datasetsProvider,
    visualizationsProvider,
    invocationsProvider,
    reportsProvider,
    interactiveToolsProvider,
];

/** Provider serving a scope, or undefined while it is not implemented yet */
export function findPaletteProvider(providerId: string): CommandPaletteProvider | undefined {
    return paletteProviders.find((provider) => provider.id === providerId);
}

const warnedUnknownIds = new Set<string>();

/** Warns once per id that names no provider, so a typo in the config does not silently disable nothing */
function warnUnknownDisabledProviders(ctx: PaletteContext) {
    for (const id of ctx.config.command_palette_disabled_providers ?? []) {
        if (!warnedUnknownIds.has(id) && !findPaletteProvider(id)) {
            warnedUnknownIds.add(id);
            const known = paletteProviders.map((provider) => provider.id).join(", ");
            console.warn(`command_palette_disabled_providers: unknown provider id "${id}" (known ids: ${known})`);
        }
    }
}

/**
 * The providers the current user may search, in registry order — what the
 * unscoped fan-out asks. A provider named in `command_palette_disabled_providers`
 * is never searched, and neither are login-only ones for an anonymous user.
 */
export function enabledPaletteProviders(ctx: PaletteContext): CommandPaletteProvider[] {
    warnUnknownDisabledProviders(ctx);
    return paletteProviders.filter((provider) => isProviderAvailable(provider.id, ctx));
}

export { parsePaletteQuery, rankPaletteItems };
export type { ParsedPaletteQuery };
