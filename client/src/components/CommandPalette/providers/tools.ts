import { faWrench } from "@fortawesome/free-solid-svg-icons";

import { type Tool, useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import type { CommandPaletteProvider, PaletteItem, ScopedSection } from "../types";
import { rankPaletteItems } from "../utilities";
import type { ScopeDefinition } from "./scopes";

/**
 * Shorter queries are answered from the hydrated tool store instead of the
 * backend — the palette can afford one or two characters because the whole
 * toolbox is already cached client side (the tool panel keeps its 3 character
 * rule for the whooshy backend search).
 */
const MIN_BACKEND_QUERY_LENGTH = 3;
/** Cap of the flat result list, and of the scoped "Tools" section */
const MAX_RESULTS = 10;
/** Cap of the favorites/recent sections shown above the scoped results */
const MAX_SECTION_ITEMS = 8;

function toolToItem(tool: Tool): PaletteItem {
    return {
        id: `tools:${tool.id}`,
        icon: faWrench,
        keywords: tool.id,
        subtitle: [tool.description, tool.panel_section_name].filter(Boolean).join(" · "),
        title: tool.name,
        to: `/?tool_id=${encodeURIComponent(tool.id)}&version=latest`,
    };
}

/** Resolves tool ids against the store cache, deduplicated and order preserving */
function itemsForToolIds(toolIds: string[]): PaletteItem[] {
    const toolStore = useToolStore();
    const seen = new Set<string>();
    return toolIds
        .filter((toolId) => {
            if (!toolId || seen.has(toolId)) {
                return false;
            }
            seen.add(toolId);
            return true;
        })
        .map((toolId) => toolStore.getToolForId(toolId))
        .filter((tool): tool is Tool => Boolean(tool))
        .map(toolToItem);
}

/**
 * Store first: the bulk tool list is fetched once and then answers every
 * keystroke locally. The palette hydrates on open, this only covers providers
 * running before that finished.
 */
async function ensureHydrated(): Promise<void> {
    const toolStore = useToolStore();
    if (Object.keys(toolStore.toolsById).length === 0) {
        await toolStore.fetchTools();
    }
}

/** Ranks the whole hydrated toolbox locally — name, id and description */
function localMatches(query: string, limit: number): PaletteItem[] {
    const toolStore = useToolStore();
    const items = Object.values(toolStore.toolsById).map(toolToItem);
    return rankPaletteItems(items, query).slice(0, limit);
}

/** Local match for short queries, backend search from `MIN_BACKEND_QUERY_LENGTH` on */
async function searchTools(query: string, limit: number): Promise<PaletteItem[]> {
    const trimmed = query.trim();
    if (!trimmed) {
        return [];
    }
    if (trimmed.length < MIN_BACKEND_QUERY_LENGTH) {
        await ensureHydrated();
        return localMatches(trimmed, limit);
    }
    const toolStore = useToolStore();
    await toolStore.fetchTools(trimmed);
    // guarded lookup: a query like "constructor" must not resolve through the prototype chain
    const resultIds = Object.hasOwn(toolStore.toolResults, trimmed) ? toolStore.toolResults[trimmed] : [];
    return itemsForToolIds(resultIds ?? []).slice(0, limit);
}

function favoriteToolItems(): PaletteItem[] {
    const userStore = useUserStore();
    return itemsForToolIds(userStore.currentFavorites.tools ?? []);
}

function recentToolItems(): PaletteItem[] {
    const userStore = useUserStore();
    return itemsForToolIds(userStore.recentTools ?? []);
}

function section(id: string, title: string, items: PaletteItem[]): ScopedSection[] {
    return items.length > 0 ? [{ id, items, title }] : [];
}

export const toolsProvider: CommandPaletteProvider = {
    id: "tools",
    title: "Tools",
    /** Recently used tools; only those already hydrated in the tool store */
    emptyQueryItems() {
        return recentToolItems();
    },
    async search(query: string) {
        return searchTools(query, MAX_RESULTS);
    },
    /**
     * `t:` scope — favorites and recently used tools on top, the actual search
     * results below with everything already listed above filtered out. An empty
     * query shows the two top sections only.
     */
    async searchScoped(_scope: ScopeDefinition, query: string): Promise<ScopedSection[]> {
        const trimmed = query.trim();
        await ensureHydrated();

        const favorites = rankPaletteItems(favoriteToolItems(), trimmed).slice(0, MAX_SECTION_ITEMS);
        const favoriteIds = new Set(favorites.map((item) => item.id));
        // the tool panel hides favorites from the recent list too
        const recent = rankPaletteItems(
            recentToolItems().filter((item) => !favoriteIds.has(item.id)),
            trimmed,
        ).slice(0, MAX_SECTION_ITEMS);

        const sections = [...section("favorites", "Favorites", favorites), ...section("recent", "Recent", recent)];
        if (!trimmed) {
            return sections;
        }

        const listed = new Set([...favorites, ...recent].map((item) => item.id));
        const results = (await searchTools(trimmed, MAX_RESULTS + listed.size))
            .filter((item) => !listed.has(item.id))
            .slice(0, MAX_RESULTS);
        return [...sections, ...section("results", "Tools", results)];
    },
};
