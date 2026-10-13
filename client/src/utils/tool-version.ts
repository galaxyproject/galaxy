/**
 * Utilities for handling tool versioning and lineage
 */

import type { Tool } from "@/stores/toolStore";

/**
 * Extracts the base tool ID from a versioned tool ID.
 * Handles both simple tool IDs (tool/version) and tool shed IDs
 * (toolshed.g2.bx.psu.edu/repos/owner/repo/tool/version)
 */
export function extractBaseToolId(toolId: string): string {
    let baseId = toolId;

    // Handle tool shed tools (format: toolshed.g2.bx.psu.edu/repos/owner/repo/tool_name/version)
    if (toolId.includes("/repos/")) {
        const parts = toolId.split("/");
        if (parts.length >= 5) {
            // Remove the version part if it exists
            const lastPart = parts[parts.length - 1];
            // Check if the last part looks like a version (contains dots or is numeric, optionally with suffix)
            // Now also handles + signs (e.g., "2.4.2+galaxy0")
            if (lastPart && /^\d+(\.\d+)*[-+\w]*$/.test(lastPart)) {
                baseId = parts.slice(0, -1).join("/");
            }
        }
    }
    // Handle simple versioned tools (format: tool_name/version)
    else if (toolId.includes("/")) {
        const parts = toolId.split("/");
        const lastPart = parts[parts.length - 1];
        // Check if the last part looks like a version
        if (lastPart && /^\d+(\.\d+)*[-+\w]*$/.test(lastPart)) {
            baseId = parts.slice(0, -1).join("/");
        }
    }

    return baseId;
}

/**
 * Compares two tool versions with a natural (numeric-aware) sort; negative when `a` is older than `b`.
 * A missing version counts as "0".
 */
export function compareToolVersions(a: string | undefined, b: string | undefined): number {
    return (a || "0").localeCompare(b || "0", undefined, { numeric: true });
}

/**
 * Filters a list of tools to show only the latest version from each lineage
 */
export function filterLatestToolVersions(tools: Tool[]): Tool[] {
    const versionGroups = new Map<string, Tool[]>();

    // Group tools by their base ID (without version)
    tools.forEach((tool) => {
        const baseId = extractBaseToolId(tool.id);

        if (!versionGroups.has(baseId)) {
            versionGroups.set(baseId, []);
        }
        versionGroups.get(baseId)!.push(tool);
    });

    // For each group, keep only the latest version
    const latestTools: Tool[] = [];
    versionGroups.forEach((toolGroup) => {
        if (toolGroup.length === 1 && toolGroup[0]) {
            latestTools.push(toolGroup[0]);
        } else if (toolGroup.length > 1) {
            // Sort by version (descending) and take the first one
            const sorted = toolGroup.sort((a, b) => compareToolVersions(b.version, a.version));
            if (sorted[0]) {
                latestTools.push(sorted[0]);
            }
        }
    });

    return latestTools;
}
