import { faWrench } from "@fortawesome/free-solid-svg-icons";

import { type Tool, useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import type {
    CommandPaletteProvider,
    PaletteContext,
    PaletteItem,
    PaletteSearchOptions,
    ScopedSection,
} from "../types";
import { rankPaletteItems } from "../utilities";
import { PALETTE_LIMITS } from "./limits";
import type { ScopeDefinition } from "./scopes";

/** Cap of the flat result list, and of the scoped "Tools" section */
const MAX_RESULTS = 10;

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

/** Local match for short queries, backend search from `PALETTE_LIMITS.minToolBackendQuery` on */
async function searchTools(query: string, limit: number): Promise<PaletteItem[]> {
    if (!query) {
        return [];
    }
    if (query.length < PALETTE_LIMITS.minToolBackendQuery) {
        await ensureHydrated();
        return localMatches(query, limit);
    }
    const toolStore = useToolStore();
    await toolStore.fetchTools(query);
    // backend ranking order, restricted to tools the hydrated toolbox knows
    return Object.values(toolStore.getToolsById(query)).map(toolToItem).slice(0, limit);
}

/** The head of the hydrated toolbox, alphabetically, as the empty `t:` fallback */
function firstTools(limit: number): PaletteItem[] {
    const toolStore = useToolStore();
    return Object.values(toolStore.toolsById)
        .map(toolToItem)
        .sort((a, b) => a.title.localeCompare(b.title))
        .slice(0, limit);
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
    async search(query: string, _ctx: PaletteContext, options: PaletteSearchOptions = {}) {
        if (options.localOnly) {
            await ensureHydrated();
            return localMatches(query, MAX_RESULTS);
        }
        return searchTools(query, MAX_RESULTS);
    },
    /**
     * `t:` scope — favorites and recently used tools on top, the actual search
     * results below with everything already listed above filtered out. An empty
     * query shows the two top sections only, or the head of the toolbox when an
     * account is new enough to have neither.
     */
    async searchScoped(_scope: ScopeDefinition, query: string): Promise<ScopedSection[]> {
        await ensureHydrated();

        const favorites = rankPaletteItems(favoriteToolItems(), query).slice(0, PALETTE_LIMITS.section);
        const favoriteIds = new Set(favorites.map((item) => item.id));
        // the tool panel hides favorites from the recent list too
        const recent = rankPaletteItems(
            recentToolItems().filter((item) => !favoriteIds.has(item.id)),
            query,
        ).slice(0, PALETTE_LIMITS.section);

        const sections = [...section("favorites", "Favorites", favorites), ...section("recent", "Recent", recent)];
        if (!query) {
            // a fresh account has neither, and an empty scope reads as broken —
            // the toolbox itself is the fallback, no request needed
            return sections.length ? sections : section("results", "Tools", firstTools(PALETTE_LIMITS.section));
        }

        const listed = new Set([...favorites, ...recent].map((item) => item.id));
        const results = (await searchTools(query, MAX_RESULTS + listed.size))
            .filter((item) => !listed.has(item.id))
            .slice(0, MAX_RESULTS);
        return [...sections, ...section("results", "Tools", results)];
    },
};
