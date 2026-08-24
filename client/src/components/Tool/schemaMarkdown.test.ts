import { describe, expect, it } from "vitest";

import { withMarkdownDescriptions } from "./schemaMarkdown";
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
                    markdownDescription: "Reference `$(inputs.input_name)`.",
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
            },
        });
    });
});
