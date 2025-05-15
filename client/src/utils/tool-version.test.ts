import type { Tool } from "@/stores/toolStore";

import { extractBaseToolId, filterLatestToolVersions } from "./tool-version";

describe("Tool Version Utilities", () => {
    describe("extractBaseToolId", () => {
        it("should handle simple tool IDs without version", () => {
            expect(extractBaseToolId("plaintools")).toBe("plaintools");
            expect(extractBaseToolId("vscode")).toBe("vscode");
        });

        it("should extract base ID from simple versioned tools", () => {
            expect(extractBaseToolId("rstudio/1.1.0")).toBe("rstudio");
            expect(extractBaseToolId("jupyter/2.0")).toBe("jupyter");
            expect(extractBaseToolId("tool/1.2.3-beta")).toBe("tool");
        });

        it("should handle tool shed tools with versions", () => {
            expect(extractBaseToolId("toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio/1.1.0")).toBe(
                "toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio"
            );

            expect(extractBaseToolId("toolshed.g2.bx.psu.edu/repos/devteam/bowtie2/bowtie2/2.4.2+galaxy0")).toBe(
                "toolshed.g2.bx.psu.edu/repos/devteam/bowtie2/bowtie2"
            );
        });

        it("should handle tool shed tools without versions", () => {
            expect(extractBaseToolId("toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio")).toBe(
                "toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio"
            );
        });

        it("should handle tools with slashes but no version", () => {
            expect(extractBaseToolId("category/subcategory/tool")).toBe("category/subcategory/tool");
            expect(extractBaseToolId("test/tool/name")).toBe("test/tool/name");
        });
    });

    describe("filterLatestToolVersions", () => {
        const createMockTool = (id: string, version: string, name = "Tool"): Tool => ({
            id,
            version,
            name,
            model_class: "InteractiveTool",
            description: "",
            labels: [],
            edam_operations: [],
            edam_topics: [],
            hidden: false,
            is_workflow_compatible: true,
            xrefs: [],
            config_file: "",
            link: "",
            min_width: 0,
            target: "",
            panel_section_id: "",
            panel_section_name: null,
            form_style: "regular",
        });

        it("should filter out older versions of tools", () => {
            const tools = [
                createMockTool("rstudio/1.1.0", "1.1.0", "RStudio"),
                createMockTool("rstudio/1.2.0", "1.2.0", "RStudio"),
                createMockTool("rstudio/1.3.1", "1.3.1", "RStudio"),
                createMockTool("jupyter/2.0", "2.0", "Jupyter"),
                createMockTool("jupyter/2.1", "2.1", "Jupyter"),
                createMockTool("vscode", "1.0", "VS Code"),
            ];

            const filtered = filterLatestToolVersions(tools);

            expect(filtered).toHaveLength(3);
            expect(filtered.find((t) => t.id.startsWith("rstudio"))?.version).toBe("1.3.1");
            expect(filtered.find((t) => t.id.startsWith("jupyter"))?.version).toBe("2.1");
            expect(filtered.find((t) => t.id === "vscode")?.version).toBe("1.0");
        });

        it("should handle tool shed tools with versioned IDs", () => {
            const tools = [
                createMockTool(
                    "toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio/1.1.0",
                    "1.1.0",
                    "RStudio Interactive"
                ),
                createMockTool(
                    "toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio/1.2.0",
                    "1.2.0",
                    "RStudio Interactive"
                ),
                createMockTool(
                    "toolshed.g2.bx.psu.edu/repos/owner/jupyter/interactive_jupyter/2.0",
                    "2.0",
                    "Jupyter Interactive"
                ),
            ];

            const filtered = filterLatestToolVersions(tools);

            expect(filtered).toHaveLength(2);
            const rstudio = filtered.find((t) => t.name.includes("RStudio"));
            const jupyter = filtered.find((t) => t.name.includes("Jupyter"));
            expect(rstudio?.version).toBe("1.2.0");
            expect(jupyter?.version).toBe("2.0");
        });

        it("should handle version formats with suffixes", () => {
            const tools = [
                createMockTool("tool/2.0.0", "2.0.0"),
                createMockTool("tool/2.0.0-beta", "2.0.0-beta"),
                createMockTool("tool/2.0.0-alpha", "2.0.0-alpha"),
            ];

            const filtered = filterLatestToolVersions(tools);

            expect(filtered).toHaveLength(1);
            // localeCompare with numeric option will order these as:
            // "2.0.0" < "2.0.0-alpha" < "2.0.0-beta"
            expect(filtered[0]?.version).toBe("2.0.0-beta");
        });

        it("should return empty array for empty input", () => {
            const filtered = filterLatestToolVersions([]);
            expect(filtered).toHaveLength(0);
        });
    });
});
