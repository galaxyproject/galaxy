import { faDesktop, faLaptopCode } from "@fortawesome/free-solid-svg-icons";

import { useEntryPointStore } from "@/stores/entryPointStore";
import { useInteractiveToolsStore } from "@/stores/interactiveToolsStore";
import { type Tool, useToolStore } from "@/stores/toolStore";
import { filterLatestToolVersions } from "@/utils/tool-version";

import type { CommandPaletteProvider, PaletteItem, ScopedSection } from "../types";
import { rankPaletteItems } from "../utilities";

/** Cap per section so the two-tier `it:` layout stays scannable */
const MAX_ITEMS_PER_SECTION = 8;

/** One running interactive tool, opened in the entry point display view */
function entryPointToItem(entryPoint: { id: string; name: string; active: boolean }): PaletteItem {
    const interactiveToolsStore = useInteractiveToolsStore();
    return {
        id: `interactiveTools:running:${entryPoint.id}`,
        icon: faDesktop,
        keywords: "running active interactive tool",
        secondaryAction: {
            label: "Stop",
            run: () => {
                // failures surface through `interactiveToolsStore.messages`
                interactiveToolsStore.stopInteractiveTool(entryPoint.id, entryPoint.name).catch(() => {});
            },
        },
        subtitle: entryPoint.active ? "Running" : "Starting…",
        title: entryPoint.name,
        to: `/interactivetool_entry_points/${entryPoint.id}/display`,
    };
}

/** One launchable interactive tool, opened in the tool form */
function toolToItem(tool: Tool): PaletteItem {
    return {
        id: `interactiveTools:${tool.id}`,
        icon: faLaptopCode,
        keywords: tool.id,
        subtitle: [tool.description, tool.panel_section_name].filter(Boolean).join(" · "),
        title: tool.name,
        to: `/?tool_id=${encodeURIComponent(tool.id)}&version=latest`,
    };
}

/**
 * Running interactive tools, store-first: the entry point store is kept fresh
 * by the app-wide SSE/polling watcher, so its cache is only hydrated here when
 * it was never fetched (first palette use before the watcher's baseline fetch).
 *
 * The store's own "loaded" flag decides that, not the length of the list: for
 * the many users with nothing running, an empty list is the answer, and reading
 * it as "not hydrated yet" would re-request `/api/entry_points` per keystroke.
 */
async function runningItems(): Promise<PaletteItem[]> {
    const entryPointStore = useEntryPointStore();
    try {
        await entryPointStore.ensureEntryPointsLoaded();
    } catch (e) {
        console.warn("Command palette could not load running interactive tools", e);
    }
    return entryPointStore.entryPoints.map(entryPointToItem);
}

/**
 * Launchable interactive tools from the tool store, latest version only —
 * same rule the interactive tools panel applies. `fetchTools()` is a no-op
 * once the toolbox has been loaded, so this stays a cache read after the
 * first call.
 */
async function availableItems(): Promise<PaletteItem[]> {
    const toolStore = useToolStore();
    if (toolStore.getInteractiveTools().length === 0) {
        try {
            await toolStore.fetchTools();
        } catch (e) {
            console.warn("Command palette could not load interactive tools", e);
        }
    }
    return filterLatestToolVersions(toolStore.getInteractiveTools()).map(toolToItem);
}

export const interactiveToolsProvider: CommandPaletteProvider = {
    id: "interactiveTools",
    title: "Interactive tools",
    /**
     * Interactive tools are also plain tools, so the unscoped fan-out is left
     * to the tools provider and this one only answers its `it:` scope.
     */
    search() {
        return [];
    },
    async searchScoped(_scope, query) {
        const [running, available] = await Promise.all([runningItems(), availableItems()]);
        const sections: ScopedSection[] = [];
        const runningMatches = rankPaletteItems(running, query).slice(0, MAX_ITEMS_PER_SECTION);
        if (runningMatches.length > 0) {
            sections.push({ id: "running", items: runningMatches, title: "Running" });
        }
        sections.push({
            id: "available",
            items: rankPaletteItems(available, query).slice(0, MAX_ITEMS_PER_SECTION),
            title: "Available",
        });
        return sections;
    },
};
