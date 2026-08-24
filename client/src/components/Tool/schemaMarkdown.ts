type JsonObject = Record<string, unknown>;
const INSTANCE_VALUE_KEYS = new Set(["const", "default", "enum", "examples"]);
export const TOOL_PROPERTY_HELP_SECTIONS: Record<string, string> = {
    class: "tool-format",
    id: "tool-format",
    name: "tool-format",
    version: "tool-format",
    description: "tool-format",
    container: "containers",
    shell_command: "expressions",
    configfiles: "configfiles",
    inputs: "parameters",
    outputs: "outputs",
    requirements: "resource-requirements",
    help: "help-content",
    tests: "testing",
    citations: "citations-metadata",
    license: "citations-metadata",
    edam_operations: "citations-metadata",
    edam_topics: "citations-metadata",
    xrefs: "citations-metadata",
    profile: "tool-format",
};

function typeDocumentationSection(path: string[], schema: JsonObject): string | undefined {
    if (path.length === 2 && path[0] === "properties") {
        return TOOL_PROPERTY_HELP_SECTIONS[path[1] ?? ""];
    }
    if (path.length === 2 && path[0] === "$defs") {
        const properties = schema.properties as JsonObject | undefined;
        const typeProperty = properties?.type as JsonObject | undefined;
        const typeName = typeProperty?.const;
        if (typeof typeName !== "string") {
            return undefined;
        }
        if (schema["x-shell-command"]) {
            return `parameter-${typeName}`;
        }
        if (path[1]?.startsWith("IncomingToolOutput")) {
            return `output-${typeName}`;
        }
    }
    return undefined;
}

function addDocumentationLink(description: string | undefined, sectionId: string): string {
    const link = `[Authoring documentation](#${sectionId})`;
    return description ? `${description}\n\n${link}` : link;
}

/** Preserve Markdown formatting in descriptions consumed by Monaco's YAML language service. */
export function withMarkdownDescriptions<T>(value: T, path: string[] = []): T {
    if (Array.isArray(value)) {
        return value.map((item, index) => withMarkdownDescriptions(item, [...path, String(index)])) as T;
    }
    if (value && typeof value === "object") {
        const result = Object.fromEntries(
            Object.entries(value as JsonObject).map(([key, item]) => [
                key,
                INSTANCE_VALUE_KEYS.has(key) ? item : withMarkdownDescriptions(item, [...path, key]),
            ]),
        ) as JsonObject;
        const description =
            typeof result.markdownDescription === "string"
                ? result.markdownDescription
                : typeof result.description === "string"
                  ? result.description
                  : undefined;
        const sectionId = typeDocumentationSection(path, result);
        if (sectionId) {
            result.markdownDescription = addDocumentationLink(description, sectionId);
        } else if (description && result.markdownDescription === undefined) {
            result.markdownDescription = description;
        }
        return result as T;
    }
    return value;
}
