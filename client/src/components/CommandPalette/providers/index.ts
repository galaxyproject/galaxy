import type { CommandPaletteProvider } from "../types";
import { type ParsedPaletteQuery, parsePaletteQuery, rankPaletteItems } from "../utilities";
import { actionsProvider } from "./actions";
import { navigationProvider } from "./navigation";
import { toolsProvider } from "./tools";

/** Ordered provider registry — results render grouped in this order */
export const paletteProviders: CommandPaletteProvider[] = [actionsProvider, navigationProvider, toolsProvider];

/** Provider serving a scope, or undefined while it is not implemented yet */
export function findPaletteProvider(providerId: string): CommandPaletteProvider | undefined {
    return paletteProviders.find((provider) => provider.id === providerId);
}

export { parsePaletteQuery, rankPaletteItems };
export type { ParsedPaletteQuery };
