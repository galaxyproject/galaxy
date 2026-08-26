import { stringify } from "yaml";

import type { AuthoringHelpSection } from "./authoringHelp";
import TOOL_SOURCE_SCHEMA from "./ToolSourceSchema.json";

interface JsonSchemaProperty {
    $ref?: string;
    const?: unknown;
    default?: unknown;
    description?: string;
    examples?: unknown[];
    items?: JsonSchemaProperty;
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

interface DiscriminatedSchema {
    discriminator: {
        mapping: Record<string, string>;
    };
}

interface ToolSourceJsonSchema {
    $defs: Record<string, JsonSchemaDefinition> & {
        YamlGalaxyToolParameter: DiscriminatedSchema;
    };
    examples?: Record<string, unknown>[];
    "x-field-order"?: string[];
    properties: {
        outputs: {
            items: DiscriminatedSchema;
        };
    };
}

interface TypeReference {
    index: string;
    sections: AuthoringHelpSection[];
}

const SCHEMA = TOOL_SOURCE_SCHEMA as ToolSourceJsonSchema;

function orderQuickStartValue(value: unknown): unknown {
    if (Array.isArray(value)) {
        return value.map(orderQuickStartValue);
    }
    if (value && typeof value === "object") {
        const fields = value as Record<string, unknown>;
        const fieldOrder = [
            "name",
            "type",
            ...Object.keys(fields).filter((field) => !["name", "type"].includes(field)),
        ];
        return Object.fromEntries(
            fieldOrder.filter((field) => field in fields).map((field) => [field, orderQuickStartValue(fields[field])]),
        );
    }
    return value;
}

export function buildQuickStartExample(): string {
    const example = SCHEMA.examples?.[0];
    if (!example) {
        throw new Error("The user tool schema has no quick-start example.");
    }
    const fieldOrder = SCHEMA["x-field-order"] ?? Object.keys(example);
    const orderedExample = Object.fromEntries(
        fieldOrder.filter((field) => field in example).map((field) => [field, orderQuickStartValue(example[field])]),
    );
    return stringify(orderedExample, { lineWidth: 0 }).trim();
}

function schemaDefinitionName(reference: string): string {
    return reference.split("/").at(-1) ?? "";
}

function markdownCell(value: string): string {
    return value.replaceAll("|", "\\|").replaceAll("\n", " ");
}

function propertyDetails(name: string, property: JsonSchemaProperty): string {
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
    if (property.examples?.length) {
        const value = property.examples[0];
        const serialized = typeof value === "string" ? value : JSON.stringify(value);
        details.push(`Example: \`${name}: ${serialized}\`.`);
    }
    return markdownCell(details.join(" ") || "No additional constraints.");
}

function propertyDefault(property: JsonSchemaProperty): string {
    return property.default === undefined ? "—" : `\`${JSON.stringify(property.default)}\``;
}

function fieldName(name: string): string {
    return name === "validators" ? "[`validators`](#validators)" : `\`${name}\``;
}

function fieldTable(definition: JsonSchemaDefinition): string[] {
    const required = new Set(definition.required ?? []);
    const fields = Object.entries(definition.properties ?? {}).map(([name, property]) => {
        return `| ${fieldName(name)} | ${propertyDetails(name, property)} | ${propertyDefault(property)} | ${required.has(name) ? "Yes" : "No"} |`;
    });
    return ["| Field | Details | Default | Required |", "| --- | --- | --- | --- |", ...fields];
}

function schemaExample(typeName: string, definition: JsonSchemaDefinition): Record<string, unknown> {
    const example = definition.examples?.[0];
    if (!example) {
        throw new Error(`Schema '${typeName}' has no example.`);
    }
    return example;
}

function referenceIndex(label: string, prefix: string, sections: AuthoringHelpSection[]): string {
    return [
        `| ${label} | Details |`,
        "| --- | --- |",
        ...sections.map((section) => {
            const typeName = section.id.replace(`${prefix}-`, "");
            const description = section.body.split("\n", 1)[0] ?? "";
            return `| [\`${typeName}\` #](#${section.id}) | ${markdownCell(description)} |`;
        }),
    ].join("\n");
}

function definitionFor(typeName: string, reference: string): JsonSchemaDefinition {
    const definition = SCHEMA.$defs[schemaDefinitionName(reference)];
    if (!definition) {
        throw new Error(`Schema '${typeName}' references an unknown definition.`);
    }
    return definition;
}

export function buildParameterTypeReference(): TypeReference {
    const mapping = SCHEMA.$defs.YamlGalaxyToolParameter.discriminator.mapping;
    const sections = Object.entries(mapping).map(([parameterType, reference]) => {
        const definition = definitionFor(parameterType, reference);
        const example = schemaExample(parameterType, definition);
        const shellCommand = definition["x-shell-command"];
        if (!shellCommand) {
            throw new Error(`Parameter schema '${parameterType}' has no shell command example.`);
        }
        const exampleYaml = stringify({ inputs: [example] }, { lineWidth: 0 }).trim();
        const shellCommandYaml = ["shell_command: |", ...shellCommand.split("\n").map((line) => `  ${line}`)].join(
            "\n",
        );
        const description = definition.description?.replaceAll("``", "`").trim() ?? "";
        return {
            id: `parameter-${parameterType}`,
            title: `${parameterType} parameter`,
            kind: "detailed-reference" as const,
            parentId: "parameter-types-reference",
            body: [
                description,
                "",
                ...fieldTable(definition),
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
    });
    return { index: referenceIndex("Parameter type", "parameter", sections), sections };
}

export function buildOutputTypeReference(): TypeReference {
    const mapping = SCHEMA.properties.outputs.items.discriminator.mapping;
    const sections = Object.entries(mapping).map(([outputType, reference]) => {
        const definition = definitionFor(outputType, reference);
        const example = schemaExample(outputType, definition);
        const exampleYaml = stringify({ outputs: [example] }, { lineWidth: 0 }).trim();
        const description = definition.description?.replaceAll("``", "`").trim() ?? "";
        return {
            id: `output-${outputType}`,
            title: `${outputType} output`,
            kind: "detailed-reference" as const,
            parentId: "output-types-reference",
            body: [
                description,
                "",
                ...fieldTable(definition),
                "",
                `Add this \`${outputType}\` output under \`outputs\`:`,
                "",
                "```yaml",
                exampleYaml,
                "```",
            ].join("\n"),
        };
    });
    return { index: referenceIndex("Output type", "output", sections), sections };
}

export function buildValidatorTypeReference(): TypeReference {
    const definitions = SCHEMA.$defs as Record<string, JsonSchemaDefinition>;
    const sections = Object.entries(definitions).flatMap(([definitionName, definition]) => {
        if (!definitionName.endsWith("ParameterValidatorModel")) {
            return [];
        }
        const validatorType = definition.properties?.type?.const;
        if (typeof validatorType !== "string") {
            return [];
        }
        const example = schemaExample(validatorType, definition);
        const exampleYaml = stringify({ validators: [example] }, { lineWidth: 0 }).trim();
        const description = definition.description?.replaceAll("``", "`").trim() ?? "";
        return [
            {
                id: `validator-${validatorType}`,
                title: `${validatorType} validator`,
                kind: "detailed-reference" as const,
                parentId: "validator-types-reference",
                body: [
                    description,
                    "",
                    ...fieldTable(definition),
                    "",
                    "Add this rule to a supported parameter's `validators` list:",
                    "",
                    "```yaml",
                    exampleYaml,
                    "```",
                ].join("\n"),
            },
        ];
    });
    return { index: referenceIndex("Validator type", "validator", sections), sections };
}
