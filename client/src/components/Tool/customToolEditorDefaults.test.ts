import { describe, expect, it } from "vitest";
import { parse } from "yaml";

import TOOL_SOURCE_SCHEMA from "./ToolSourceSchema.json";
import { CLEAR_TOOL_YAML, NEW_TOOL_YAML } from "./customToolEditorDefaults";

describe("custom tool editor defaults", () => {
    it("preloads the schema-derived Getting Started example", () => {
        expect(parse(NEW_TOOL_YAML)).toEqual(TOOL_SOURCE_SCHEMA.examples[0]);
    });

    it("provides the minimal clear-tool skeleton", () => {
        expect(CLEAR_TOOL_YAML).toBe(`class: GalaxyUserTool
name:
version: "0.1.0"
container:
shell_command:
inputs: []
outputs: []`);
    });
});
