import { stringify } from "yaml";

import TOOL_SOURCE_SCHEMA from "./ToolSourceSchema.json";

interface ToolSourceJsonSchema {
    examples?: Record<string, unknown>[];
}

const QUICK_START_FIELD_ORDER = [
    "class",
    "id",
    "name",
    "version",
    "description",
    "container",
    "shell_command",
    "inputs",
    "outputs",
];

function orderExampleValue(value: unknown): unknown {
    if (Array.isArray(value)) {
        return value.map(orderExampleValue);
    }
    if (value && typeof value === "object") {
        const fields = value as Record<string, unknown>;
        const fieldOrder = [
            "name",
            "type",
            ...Object.keys(fields).filter((field) => !["name", "type"].includes(field)),
        ];
        return Object.fromEntries(
            fieldOrder.filter((field) => field in fields).map((field) => [field, orderExampleValue(fields[field])]),
        );
    }
    return value;
}

export function buildNewToolYaml(schema: ToolSourceJsonSchema = TOOL_SOURCE_SCHEMA): string {
    const example = schema.examples?.[0];
    if (!example) {
        throw new Error("The user tool schema has no Getting Started example.");
    }
    const orderedExample = Object.fromEntries(
        QUICK_START_FIELD_ORDER.filter((field) => field in example).map((field) => [
            field,
            orderExampleValue(example[field]),
        ]),
    );
    return stringify(orderedExample, { lineWidth: 0 }).trim();
}

export const NEW_TOOL_YAML = buildNewToolYaml();

export const CLEAR_TOOL_YAML = `class: GalaxyUserTool
name:
version: "0.1.0"
container:
shell_command:
inputs: []
outputs: []`;
