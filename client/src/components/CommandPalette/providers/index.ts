import type { CommandPaletteProvider, PaletteContext } from "../types";
import { type ParsedPaletteQuery, parsePaletteQuery, rankPaletteItems } from "../utilities";
import { actionsProvider } from "./actions";
import { datasetsProvider } from "./datasets";
import { historiesProvider } from "./histories";
import { interactiveToolsProvider } from "./interactiveTools";
import { invocationsProvider } from "./invocations";
import { navigationProvider } from "./navigation";
import { pagesProvider } from "./pages";
import { isProviderEnabled } from "./scopes";
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
    pagesProvider,
    interactiveToolsProvider,
];

/** Provider serving a scope, or undefined while it is not implemented yet */
export function findPaletteProvider(providerId: string): CommandPaletteProvider | undefined {
    return paletteProviders.find((provider) => provider.id === providerId);
}

/**
 * The providers this instance left on, in registry order — what the unscoped
 * fan-out asks. A provider named in `command_palette_disabled_providers` is
 * never searched, and neither its scopes nor its category are offered.
 */
export function enabledPaletteProviders(ctx: PaletteContext): CommandPaletteProvider[] {
    return paletteProviders.filter((provider) => isProviderEnabled(provider.id, ctx));
}

export { parsePaletteQuery, rankPaletteItems };
export type { ParsedPaletteQuery };
