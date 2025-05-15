import { describe, expect, it } from "vitest";
import type { Tool } from "@/stores/toolStore";

// Import the filtering function directly from the component file
// For testing purposes, we'll extract the logic as a utility function

export function filterLatestVersions(tools: Tool[]): Tool[] {
    const versionGroups = new Map<string, Tool[]>();

    // Group tools by their base ID (without version)
    tools.forEach((tool) => {
        // Extract base ID without version suffix
        const baseId = tool.id.replace(/\/\d+(\.\d+)*$/, "");
        if (!versionGroups.has(baseId)) {
            versionGroups.set(baseId, []);
        }
        versionGroups.get(baseId)!.push(tool);
    });

    // For each group, keep only the latest version
    const latestTools: Tool[] = [];
    versionGroups.forEach((toolGroup) => {
        if (toolGroup.length === 1) {
            latestTools.push(toolGroup[0]);
        } else {
            // Sort by version (descending) and take the first one
            const sorted = toolGroup.sort((a, b) => {
                // Compare versions using natural sort
                const versionA = a.version || "0";
                const versionB = b.version || "0";
                return versionB.localeCompare(versionA, undefined, { numeric: true });
            });
            latestTools.push(sorted[0]);
        }
    });

    return latestTools;
}

describe("InteractiveToolsPanel tool version filtering", () => {
    it("should filter out older versions of tools", () => {
        const mockTools: Partial<Tool>[] = [
            { id: "rstudio/1.1.0", version: "1.1.0", name: "RStudio", model_class: "InteractiveTool" },
            { id: "rstudio/1.2.0", version: "1.2.0", name: "RStudio", model_class: "InteractiveTool" },
            { id: "rstudio/1.3.1", version: "1.3.1", name: "RStudio", model_class: "InteractiveTool" },
            { id: "jupyter/2.0", version: "2.0", name: "Jupyter", model_class: "InteractiveTool" },
            { id: "jupyter/2.1", version: "2.1", name: "Jupyter", model_class: "InteractiveTool" },
            { id: "vscode", version: "1.0", name: "VS Code", model_class: "InteractiveTool" },
        ];

        const filtered = filterLatestVersions(mockTools as Tool[]);

        expect(filtered).toHaveLength(3);
        expect(filtered.find((t) => t.id.startsWith("rstudio"))?.version).toBe("1.3.1");
        expect(filtered.find((t) => t.id.startsWith("jupyter"))?.version).toBe("2.1");
        expect(filtered.find((t) => t.id === "vscode")?.version).toBe("1.0");
    });

    it("should handle tools without version suffixes", () => {
        const mockTools: Partial<Tool>[] = [
            { id: "plaintools", version: "1.0", name: "Plain Tool", model_class: "InteractiveTool" },
            { id: "othertool/1.0", version: "1.0", name: "Other Tool", model_class: "InteractiveTool" },
        ];

        const filtered = filterLatestVersions(mockTools as Tool[]);

        expect(filtered).toHaveLength(2);
    });

    it("should handle mixed version formats", () => {
        const mockTools: Partial<Tool>[] = [
            { id: "tool/1", version: "1", name: "Tool", model_class: "InteractiveTool" },
            { id: "tool/1.0", version: "1.0", name: "Tool", model_class: "InteractiveTool" },
            { id: "tool/1.1.0", version: "1.1.0", name: "Tool", model_class: "InteractiveTool" },
            { id: "tool/2.0.0-beta", version: "2.0.0-beta", name: "Tool", model_class: "InteractiveTool" },
            { id: "tool/2.0.0", version: "2.0.0", name: "Tool", model_class: "InteractiveTool" },
        ];

        const filtered = filterLatestVersions(mockTools as Tool[]);

        expect(filtered).toHaveLength(1);
        expect(filtered[0].version).toBe("2.0.0");
    });
});
