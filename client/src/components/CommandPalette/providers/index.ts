import type { CommandPaletteProvider } from "../types";
import { type ParsedPaletteQuery, parsePaletteQuery as parseQuery, rankPaletteItems } from "../utilities";
import { actionsProvider } from "./actions";
import { navigationProvider } from "./navigation";
import { toolsProvider } from "./tools";

/** Ordered provider registry — results render grouped in this order */
export const paletteProviders: CommandPaletteProvider[] = [actionsProvider, navigationProvider, toolsProvider];

export function parsePaletteQuery(raw: string): ParsedPaletteQuery {
    return parseQuery(raw, paletteProviders);
}

export { rankPaletteItems };
export type { ParsedPaletteQuery };
