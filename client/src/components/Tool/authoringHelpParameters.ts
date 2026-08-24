import { stringify } from "yaml";

import type { AuthoringHelpSection } from "./authoringHelp";
import TOOL_SOURCE_SCHEMA from "./ToolSourceSchema.json";

interface JsonSchemaProperty {
    const?: unknown;
    default?: unknown;
    description?: string;
    type?: string;
    anyOf?: JsonSchemaProperty[];
}

interface JsonSchemaDefinition {
    description?: string;
    examples?: Record<string, unknown>[];
    properties?: Record<string, JsonSchemaProperty>;
    required?: string[];
    "x-shell-command"?: string;
}

interface ToolSourceJsonSchema {
    $defs: Record<string, JsonSchemaDefinition> & {
        YamlGalaxyToolParameter: {
            discriminator: {
                mapping: Record<string, string>;
            };
        };
    };
}

interface ParameterTypeReference {
    index: string;
    sections: AuthoringHelpSection[];
}

const SCHEMA = TOOL_SOURCE_SCHEMA as ToolSourceJsonSchema;

function schemaDefinitionName(reference: string): string {
    return reference.split("/").at(-1) ?? "";
}

function markdownCell(value: string): string {
    return value.replaceAll("|", "\\|").replaceAll("\n", " ");
}

function propertyDetails(property: JsonSchemaProperty): string {
    const details: string[] = [];
    if (property.description) {
        details.push(property.description.trim());
    } else if (property.const !== undefined) {
        details.push(`Must be \`${String(property.const)}\`.`);
    } else {
        const types = property.anyOf?.flatMap((option) => option.type ?? []) ?? (property.type ? [property.type] : []);
        if (types.length) {
            details.push(`Type: ${types.map((type) => `\`${type}\``).join(" or ")}.`);
        }
    }
    return markdownCell(details.join(" ") || "No additional constraints.");
}

function propertyDefault(property: JsonSchemaProperty): string {
    return property.default === undefined ? "—" : `\`${JSON.stringify(property.default)}\``;
}

function parameterSection(parameterType: string, definition: JsonSchemaDefinition): AuthoringHelpSection {
    const example = definition.examples?.[0];
    if (!example) {
        throw new Error(`Parameter schema '${parameterType}' has no example.`);
    }
    const shellCommand = definition["x-shell-command"];
    if (!shellCommand) {
        throw new Error(`Parameter schema '${parameterType}' has no shell command example.`);
    }
    const required = new Set(definition.required ?? []);
    const fields = Object.entries(definition.properties ?? {}).map(([name, property]) => {
        return `| \`${name}\` | ${propertyDetails(property)} | ${propertyDefault(property)} | ${required.has(name) ? "Yes" : "No"} |`;
    });
    const exampleYaml = stringify({ inputs: [example] }, { lineWidth: 0 }).trim();
    const shellCommandYaml = ["shell_command: |", ...shellCommand.split("\n").map((line) => `  ${line}`)].join("\n");
    const description = definition.description?.replaceAll("``", "`").trim() ?? "";
    return {
        id: `parameter-${parameterType}`,
        title: `${parameterType} parameter`,
        kind: "reference",
        parentId: "parameters",
        body: [
            description,
            "",
            "| Field | Details | Default | Required |",
            "| --- | --- | --- | --- |",
            ...fields,
            "",
            `Add this \`${parameterType}\` parameter under \`inputs\`:`,
            "",
            "```yaml",
            exampleYaml,
            "```",
            "",
            "Use the parameter in `shell_command` like this:",
            "",
            "```yaml",
            shellCommandYaml,
            "```",
        ].join("\n"),
    };
}

export function buildParameterTypeReference(): ParameterTypeReference {
    const mapping = SCHEMA.$defs.YamlGalaxyToolParameter.discriminator.mapping;
    const sections = Object.entries(mapping).map(([parameterType, reference]) => {
        const definition = SCHEMA.$defs[schemaDefinitionName(reference)];
        if (!definition) {
            throw new Error(`Parameter schema '${parameterType}' references an unknown definition.`);
        }
        return parameterSection(parameterType, definition);
    });
    const index = [
        "| Parameter type | Details |",
        "| --- | --- |",
        ...sections.map((section) => {
            const parameterType = section.id.replace("parameter-", "");
            const description = section.body.split("\n", 1)[0] ?? "";
            return `| [\`${parameterType}\`](#${section.id}) | ${markdownCell(description)} |`;
        }),
    ].join("\n");
    return { index, sections };
}
