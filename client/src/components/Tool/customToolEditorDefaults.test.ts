import { describe, expect, it } from "vitest";
import { parse } from "yaml";

import { buildNewToolYaml, CLEAR_TOOL_YAML, NEW_TOOL_YAML } from "./customToolEditorDefaults";
import TOOL_SOURCE_SCHEMA from "./ToolSourceSchema.json";

describe("custom tool editor defaults", () => {
    it("builds the new-tool value from the schema Getting Started example", () => {
        expect(NEW_TOOL_YAML).toBe(buildNewToolYaml());
        expect(parse(NEW_TOOL_YAML)).toEqual(TOOL_SOURCE_SCHEMA.examples[0]);
    });

    it("fails clearly when the schema has no Getting Started example", () => {
        expect(() => buildNewToolYaml({})).toThrow("The user tool schema has no Getting Started example.");
    });

    it("provides the exact minimal clear-tool skeleton", () => {
        expect(CLEAR_TOOL_YAML).toBe(`class: GalaxyUserTool
name:
version: "0.1.0"
container:
shell_command:
inputs: []
outputs: []`);
    });
});
