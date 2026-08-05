/**
 * Utilities for handling tool versioning and lineage
 */

import type { Tool } from "@/stores/toolStore";

/** Matches segments that look like a version (e.g. "1.13", "2.4.2+galaxy0"). */
const VERSION_SEGMENT_REGEX = /^\d+(\.\d+)*[-+\w]*$/;

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
            if (lastPart && VERSION_SEGMENT_REGEX.test(lastPart)) {
                baseId = parts.slice(0, -1).join("/");
            }
        }
    }
    // Handle simple versioned tools (format: tool_name/version)
    else if (toolId.includes("/")) {
        const parts = toolId.split("/");
        const lastPart = parts[parts.length - 1];
        // Check if the last part looks like a version
        if (lastPart && VERSION_SEGMENT_REGEX.test(lastPart)) {
            baseId = parts.slice(0, -1).join("/");
        }
    }

    return baseId;
}

export interface RequestedToolParts {
    tool_shed_id?: string;
    name: string;
    requested_version?: string;
}

/**
 * Splits a tool id into the parts of a tool installation request entry.
 * Tool-shed tools use ids of the form
 * `<shed host>/repos/<owner>/<repo>/<tool id>[/<version>]`, from which the
 * shed repository id, tool name, and version are derived (the trailing segment
 * is treated as a version only when it looks like one, mirroring
 * `extractBaseToolId`); anything else (e.g. a local tool id) only identifies
 * the tool by name.
 */
export function parseRequestedToolParts(toolId: string): RequestedToolParts {
    const match = toolId.match(/^(.+\/repos\/[^/]+\/[^/]+)\/(.+)$/);
    const toolShedId = match?.[1];
    const rest = match?.[2];
    if (!toolShedId || !rest) {
        return { name: toolId };
    }
    const segments = rest.split("/");
    const lastSegment = segments[segments.length - 1];
    let requestedVersion: string | undefined;
    if (segments.length > 1 && lastSegment && VERSION_SEGMENT_REGEX.test(lastSegment)) {
        segments.pop();
        requestedVersion = lastSegment;
    }
    return { tool_shed_id: toolShedId, name: segments.join("/"), requested_version: requestedVersion };
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
            const sorted = toolGroup.sort((a, b) => {
                // Compare versions using natural sort
                const versionA = a.version || "0";
                const versionB = b.version || "0";
                return versionB.localeCompare(versionA, undefined, { numeric: true });
            });
            if (sorted[0]) {
                latestTools.push(sorted[0]);
            }
        }
    });

    return latestTools;
}
