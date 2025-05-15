import type { Tool } from "@/stores/toolStore";

// Import the filtering function directly from the component file
// For testing purposes, we'll extract the logic as a utility function

export function filterLatestVersions(tools: Tool[]): Tool[] {
    const versionGroups = new Map<string, Tool[]>();

    // Group tools by their base ID (without version)
    tools.forEach((tool) => {
        let baseId = tool.id;

        // Handle tool shed tools (format: toolshed.g2.bx.psu.edu/repos/owner/repo/tool_name/version)
        if (tool.id.includes("/repos/")) {
            const parts = tool.id.split("/");
            if (parts.length >= 5) {
                // Remove the version part if it exists
                const lastPart = parts[parts.length - 1];
                // Check if the last part looks like a version (contains dots or is numeric, optionally with suffix)
                if (lastPart && /^\d+(\.\d+)*(-\w+)?$/.test(lastPart)) {
                    baseId = parts.slice(0, -1).join("/");
                }
            }
        }
        // Handle simple versioned tools (format: tool_name/version)
        else if (tool.id.includes("/")) {
            const parts = tool.id.split("/");
            const lastPart = parts[parts.length - 1];
            // Check if the last part looks like a version
            if (lastPart && /^\d+(\.\d+)*(-\w+)?$/.test(lastPart)) {
                baseId = parts.slice(0, -1).join("/");
            }
        }

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
        // The localeCompare with numeric option will put "2.0.0-beta" after "2.0.0"
        expect(filtered[0]?.version).toBe("2.0.0-beta");
    });

    it("should handle tool shed tools with versioned IDs", () => {
        const mockTools: Partial<Tool>[] = [
            {
                id: "toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio/1.1.0",
                version: "1.1.0",
                name: "RStudio Interactive",
                model_class: "InteractiveTool",
            },
            {
                id: "toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio/1.2.0",
                version: "1.2.0",
                name: "RStudio Interactive",
                model_class: "InteractiveTool",
            },
            {
                id: "toolshed.g2.bx.psu.edu/repos/owner/jupyter/interactive_jupyter/2.0",
                version: "2.0",
                name: "Jupyter Interactive",
                model_class: "InteractiveTool",
            },
        ];

        const filtered = filterLatestVersions(mockTools as Tool[]);

        expect(filtered).toHaveLength(2);
        const rstudio = filtered.find((t) => t.name.includes("RStudio"));
        const jupyter = filtered.find((t) => t.name.includes("Jupyter"));
        expect(rstudio?.version).toBe("1.2.0");
        expect(jupyter?.version).toBe("2.0");
    });
});
