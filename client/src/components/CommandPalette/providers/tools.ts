import { faWrench } from "@fortawesome/free-solid-svg-icons";

import { type Tool, useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import type { CommandPaletteProvider, PaletteItem } from "../types";

/** Same threshold the tool panel search uses before hitting the backend */
const MIN_QUERY_LENGTH = 3;
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

export const toolsProvider: CommandPaletteProvider = {
    id: "tools",
    prefix: "t",
    title: "Tools",
    /** Recently used tools; only those already hydrated in the tool store */
    emptyQueryItems() {
        const toolStore = useToolStore();
        const userStore = useUserStore();
        return userStore.recentTools
            .map((toolId) => toolStore.getToolForId(toolId))
            .filter((tool): tool is Tool => Boolean(tool))
            .map(toolToItem);
    },
    async search(query: string) {
        const trimmed = query.trim();
        if (trimmed.length < MIN_QUERY_LENGTH) {
            return [];
        }
        const toolStore = useToolStore();
        await toolStore.fetchTools(trimmed);
        const matchedIds = toolStore.toolResults[trimmed] ?? [];
        return matchedIds
            .map((toolId) => toolStore.getToolForId(toolId))
            .filter((tool): tool is Tool => Boolean(tool))
            .slice(0, MAX_RESULTS)
            .map(toolToItem);
    },
};
