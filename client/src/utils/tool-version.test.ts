import { getFakeTool } from "@tests/test-data/tools";
import { describe, expect, it } from "vitest";

import { extractBaseToolId, filterLatestToolVersions, parseRequestedToolParts } from "./tool-version";

describe("Tool Version Utilities", () => {
    describe("extractBaseToolId", () => {
        it.each([
            { name: "an unversioned plain tool", id: "plaintools", expected: "plaintools" },
            { name: "an unversioned VS Code tool", id: "vscode", expected: "vscode" },
            { name: "a three-part version", id: "rstudio/1.1.0", expected: "rstudio" },
            { name: "a two-part version", id: "jupyter/2.0", expected: "jupyter" },
            { name: "a version with a prerelease suffix", id: "tool/1.2.3-beta", expected: "tool" },
            {
                name: "a versioned tool shed tool",
                id: "toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio/1.1.0",
                expected: "toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio",
            },
            {
                name: "a tool shed version with a build suffix",
                id: "toolshed.g2.bx.psu.edu/repos/devteam/bowtie2/bowtie2/2.4.2+galaxy0",
                expected: "toolshed.g2.bx.psu.edu/repos/devteam/bowtie2/bowtie2",
            },
            {
                name: "an unversioned tool shed tool",
                id: "toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio",
                expected: "toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio",
            },
            {
                name: "a category path without a version",
                id: "category/subcategory/tool",
                expected: "category/subcategory/tool",
            },
            { name: "a slash-separated name without a version", id: "test/tool/name", expected: "test/tool/name" },
        ])("extracts the base id of $name", ({ id, expected }) => {
            expect(extractBaseToolId(id)).toBe(expected);
        });
    });

    describe("parseRequestedToolParts", () => {
        it.each([
            {
                name: "a versioned BWA tool shed tool",
                id: "toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17",
                expected: {
                    tool_shed_id: "toolshed.g2.bx.psu.edu/repos/devteam/bwa",
                    name: "bwa",
                    requested_version: "0.7.17",
                },
            },
            {
                name: "a tool shed version with a build suffix",
                id: "toolshed.g2.bx.psu.edu/repos/devteam/bowtie2/bowtie2/2.4.2+galaxy0",
                expected: {
                    tool_shed_id: "toolshed.g2.bx.psu.edu/repos/devteam/bowtie2",
                    name: "bowtie2",
                    requested_version: "2.4.2+galaxy0",
                },
            },
            {
                name: "a version carrying a dot after the build separator",
                id: "toolshed.g2.bx.psu.edu/repos/iuc/snpeff/snpEff/4.3+T.galaxy1",
                expected: {
                    tool_shed_id: "toolshed.g2.bx.psu.edu/repos/iuc/snpeff",
                    name: "snpEff",
                    requested_version: "4.3+T.galaxy1",
                },
            },
            {
                name: "an unversioned tool shed tool",
                id: "toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa_tool",
                expected: {
                    tool_shed_id: "toolshed.g2.bx.psu.edu/repos/devteam/bwa",
                    name: "bwa_tool",
                    requested_version: undefined,
                },
            },
            {
                name: "a tool shed name containing an unversioned trailing segment",
                id: "toolshed.g2.bx.psu.edu/repos/owner/repo/tool/subtool",
                expected: {
                    tool_shed_id: "toolshed.g2.bx.psu.edu/repos/owner/repo",
                    name: "tool/subtool",
                    requested_version: undefined,
                },
            },
            { name: "a local Cut tool", id: "Cut1", expected: { name: "Cut1" } },
            {
                name: "a local interactive tool",
                id: "interactive_tool_jupyter",
                expected: { name: "interactive_tool_jupyter" },
            },
        ])("parses $name", ({ id, expected }) => {
            expect(parseRequestedToolParts(id)).toEqual(expected);
        });
    });

    describe("filterLatestToolVersions", () => {
        it("keeps the newest version of each local tool", () => {
            const tools = [
                getFakeTool({ id: "rstudio/1.1.0", version: "1.1.0", name: "RStudio", model_class: "InteractiveTool" }),
                getFakeTool({ id: "rstudio/1.2.0", version: "1.2.0", name: "RStudio", model_class: "InteractiveTool" }),
                getFakeTool({ id: "rstudio/1.3.1", version: "1.3.1", name: "RStudio", model_class: "InteractiveTool" }),
                getFakeTool({ id: "jupyter/2.0", version: "2.0", name: "Jupyter", model_class: "InteractiveTool" }),
                getFakeTool({ id: "jupyter/2.1", version: "2.1", name: "Jupyter", model_class: "InteractiveTool" }),
                getFakeTool({ id: "vscode", version: "1.0", name: "VS Code", model_class: "InteractiveTool" }),
            ];

            const filtered = filterLatestToolVersions(tools);

            expect(filtered).toHaveLength(3);
            expect(filtered.find((t) => t.id.startsWith("rstudio"))?.version).toBe("1.3.1");
            expect(filtered.find((t) => t.id.startsWith("jupyter"))?.version).toBe("2.1");
            expect(filtered.find((t) => t.id === "vscode")?.version).toBe("1.0");
        });

        it("keeps the newest version of each tool shed tool", () => {
            const tools = [
                getFakeTool({
                    id: "toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio/1.1.0",
                    version: "1.1.0",
                    name: "RStudio Interactive",
                    model_class: "InteractiveTool",
                }),
                getFakeTool({
                    id: "toolshed.g2.bx.psu.edu/repos/owner/rstudio/interactive_rstudio/1.2.0",
                    version: "1.2.0",
                    name: "RStudio Interactive",
                    model_class: "InteractiveTool",
                }),
                getFakeTool({
                    id: "toolshed.g2.bx.psu.edu/repos/owner/jupyter/interactive_jupyter/2.0",
                    version: "2.0",
                    name: "Jupyter Interactive",
                    model_class: "InteractiveTool",
                }),
            ];

            const filtered = filterLatestToolVersions(tools);

            expect(filtered).toHaveLength(2);
            const rstudio = filtered.find((t) => t.name.includes("RStudio"));
            const jupyter = filtered.find((t) => t.name.includes("Jupyter"));
            expect(rstudio?.version).toBe("1.2.0");
            expect(jupyter?.version).toBe("2.0");
        });

        it("orders version suffixes using numeric locale comparison", () => {
            const tools = [
                getFakeTool({ id: "tool/2.0.0", version: "2.0.0", name: "Tool", model_class: "InteractiveTool" }),
                getFakeTool({
                    id: "tool/2.0.0-beta",
                    version: "2.0.0-beta",
                    name: "Tool",
                    model_class: "InteractiveTool",
                }),
                getFakeTool({
                    id: "tool/2.0.0-alpha",
                    version: "2.0.0-alpha",
                    name: "Tool",
                    model_class: "InteractiveTool",
                }),
            ];

            const filtered = filterLatestToolVersions(tools);

            expect(filtered).toHaveLength(1);
            // localeCompare with numeric option will order these as:
            // "2.0.0" < "2.0.0-alpha" < "2.0.0-beta"
            expect(filtered[0]?.version).toBe("2.0.0-beta");
        });

        it("returns no tools for an empty input", () => {
            const filtered = filterLatestToolVersions([]);
            expect(filtered).toHaveLength(0);
        });
    });
});
