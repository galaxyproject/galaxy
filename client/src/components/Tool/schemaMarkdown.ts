type JsonObject = Record<string, unknown>;
const INSTANCE_VALUE_KEYS = new Set(["const", "default", "enum", "examples"]);

export const TOOL_SOURCE_SCHEMA_URI = "https://schema.galaxyproject.org/customTool.json";

/** Preserve Markdown formatting in descriptions consumed by Monaco's YAML language service. */
export function withMarkdownDescriptions<T>(value: T): T {
    if (Array.isArray(value)) {
        return value.map((item) => withMarkdownDescriptions(item)) as T;
    }
    if (value && typeof value === "object") {
        const result = Object.fromEntries(
            Object.entries(value as JsonObject).map(([key, item]) => [
                key,
                INSTANCE_VALUE_KEYS.has(key) ? item : withMarkdownDescriptions(item),
            ]),
        ) as JsonObject;
        if (typeof result.description === "string" && result.markdownDescription === undefined) {
            result.markdownDescription = result.description;
        }
        return result as T;
    }
    return value;
}
