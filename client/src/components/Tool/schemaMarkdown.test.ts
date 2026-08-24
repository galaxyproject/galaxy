import { describe, expect, it } from "vitest";

import { authoringHelpSections } from "./authoringHelp";
import { TOOL_PROPERTY_HELP_SECTIONS, withMarkdownDescriptions } from "./schemaMarkdown";
import TOOL_SOURCE_SCHEMA from "./ToolSourceSchema.json";

describe("schema Markdown descriptions", () => {
    it("preserves inline code in nested schema descriptions", () => {
        const schema = {
            description: "Use `shell_command`.",
            properties: {
                inputs: {
                    description: "Reference `$(inputs.input_name)`.",
                },
            },
        };

        const result = withMarkdownDescriptions(schema);

        expect(result).toMatchObject({
            markdownDescription: "Use `shell_command`.",
            properties: {
                inputs: {
                    markdownDescription: expect.stringContaining("Reference `$(inputs.input_name)`."),
                },
            },
        });
        expect(schema).not.toHaveProperty("markdownDescription");
    });

    it("keeps an explicit Markdown description", () => {
        const schema = {
            description: "Plain description.",
            markdownDescription: "Description with **emphasis**.",
        };

        expect(withMarkdownDescriptions(schema).markdownDescription).toBe("Description with **emphasis**.");
    });

    it("does not treat example values as schemas", () => {
        const schema = {
            examples: [{ description: "An instance field." }],
        };

        expect(withMarkdownDescriptions(schema)).toEqual(schema);
    });

    it("adds Markdown hover content to the editor tool schema", () => {
        const result = withMarkdownDescriptions(TOOL_SOURCE_SCHEMA);

        expect(result).toMatchObject({
            properties: {
                shell_command: {
                    markdownDescription: expect.stringContaining("`$(inputs.input_name)`"),
                },
                inputs: {
                    markdownDescription: expect.stringContaining("[Authoring documentation](#parameters)"),
                },
                outputs: {
                    markdownDescription: expect.stringContaining("[Authoring documentation](#outputs)"),
                },
            },
        });
    });

    it("links parameter and output definitions to their matching reference sections", () => {
        const result = withMarkdownDescriptions(TOOL_SOURCE_SCHEMA);
        const definitions = result.$defs as unknown as Record<string, { markdownDescription?: string }>;

        expect(definitions.YamlIntegerParameter?.markdownDescription).toContain("(#parameter-integer)");
        expect(definitions.IncomingToolOutputDataset?.markdownDescription).toContain("(#output-data)");
    });

    it("defines documentation targets for every top-level tool property", () => {
        const sectionIds = new Set(authoringHelpSections.map((section) => section.id));

        expect(Object.keys(TOOL_SOURCE_SCHEMA.properties).every((name) => TOOL_PROPERTY_HELP_SECTIONS[name])).toBe(
            true,
        );
        expect(Object.values(TOOL_PROPERTY_HELP_SECTIONS).every((sectionId) => sectionIds.has(sectionId))).toBe(true);
    });
});
