import { describe, expect, it } from "vitest";
import { parse } from "yaml";

import {
    authoringHelpGroups,
    authoringHelpIntro,
    authoringHelpSections,
    authoringHelpTitle,
    linkSchemaKeys,
    linkedAuthoringHelpSection,
    resolveDocLinks,
} from "./authoringHelp";
import TOOL_SOURCE_SCHEMA from "./ToolSourceSchema.json";

describe("user-defined tool authoring help", () => {
    it("loads the shared help content", () => {
        expect(authoringHelpTitle).toBe("Authoring User-Defined Tools");
        expect(authoringHelpIntro).toContain("User-defined tools let a user register");
        expect(authoringHelpSections.length).toBeGreaterThan(0);
        expect(new Set(authoringHelpSections.map((section) => section.id)).size).toBe(authoringHelpSections.length);
        expect(authoringHelpGroups.map((group) => group.title)).toEqual([
            "Getting Started",
            "Reference",
            "Detailed reference",
            "Common questions",
        ]);
        expect(authoringHelpGroups.every((group) => group.sections.length > 0)).toBe(true);
        expect(authoringHelpGroups[0]?.sections.map((section) => section.id)).toEqual(["quick-start"]);
    });

    it("renders the schema quick-start example", () => {
        const quickStart = authoringHelpSections.find((section) => section.id === "quick-start");
        const yamlExample = quickStart?.body.match(/```yaml\n([\s\S]+?)\n```/)?.[1];

        expect(TOOL_SOURCE_SCHEMA.examples).toHaveLength(1);
        expect(parse(yamlExample!)).toEqual(TOOL_SOURCE_SCHEMA.examples[0]);
    });

    it("builds one navigable reference entry per parameter schema example", () => {
        const definitions = TOOL_SOURCE_SCHEMA.$defs as Record<string, unknown>;
        const mapping = TOOL_SOURCE_SCHEMA.$defs.YamlGalaxyToolParameter.discriminator.mapping;
        const parameterSections = authoringHelpSections.filter(
            (section) => section.parentId === "parameter-types-reference",
        );
        const parameterIndex = authoringHelpSections.find((section) => section.id === "parameters");

        expect(parameterSections.map((section) => section.id)).toEqual(
            Object.keys(mapping).map((parameterType) => `parameter-${parameterType}`),
        );
        for (const section of parameterSections) {
            const parameterType = section.id.replace("parameter-", "");
            const definitionName = mapping[parameterType as keyof typeof mapping].split("/").at(-1)!;
            const definition = definitions[definitionName] as {
                examples: Array<Record<string, unknown>>;
                "x-shell-command": string;
            };
            const yamlExamples = [...section.body.matchAll(/```yaml\n([\s\S]+?)\n```/g)].map((match) => match[1]);
            const inputExample = yamlExamples[0];
            const shellCommandExample = yamlExamples[1];

            expect(parameterIndex?.body).toContain(`](#${section.id})`);
            expect(parameterIndex?.body).toContain(`\` #](#${section.id})`);
            expect(section.kind).toBe("detailed-reference");
            expect(section.parentId).toBe("parameter-types-reference");
            expect(yamlExamples).toHaveLength(2);
            expect(section.body).toContain(`Add this \`${parameterType}\` parameter under \`inputs\``);
            expect(parse(inputExample!).inputs[0]).toEqual(definition.examples[0]);
            expect(parse(shellCommandExample!).shell_command.trim()).toBe(definition["x-shell-command"]);
        }
    });

    it("builds one navigable reference entry per output schema example", () => {
        const definitions = TOOL_SOURCE_SCHEMA.$defs as Record<string, unknown>;
        const mapping = TOOL_SOURCE_SCHEMA.properties.outputs.items.discriminator.mapping;
        const outputSections = authoringHelpSections.filter((section) => section.parentId === "output-types-reference");
        const outputIndex = authoringHelpSections.find((section) => section.id === "outputs");

        expect(Object.keys(mapping)).toEqual(["collection", "data"]);

        expect(outputSections.map((section) => section.id)).toEqual(
            Object.keys(mapping).map((outputType) => `output-${outputType}`),
        );
        for (const section of outputSections) {
            const outputType = section.id.replace("output-", "");
            const definitionName = mapping[outputType as keyof typeof mapping].split("/").at(-1)!;
            const definition = definitions[definitionName] as { examples: Array<Record<string, unknown>> };
            const yamlExample = section.body.match(/```yaml\n([\s\S]+?)\n```/)?.[1];

            expect(outputIndex?.body).toContain(`](#${section.id})`);
            expect(outputIndex?.body).toContain(`\` #](#${section.id})`);
            expect(section.kind).toBe("detailed-reference");
            expect(section.parentId).toBe("output-types-reference");
            expect(section.body).toContain(`Add this \`${outputType}\` output under \`outputs\``);
            expect(parse(yamlExample!).outputs[0]).toEqual(definition.examples[0]);
        }

        const dataOutput = outputSections.find((section) => section.id === "output-data");
        const dataOutputDefinitionName = mapping.data.split("/").at(-1)!;
        const dataOutputDefinition = definitions[dataOutputDefinitionName] as {
            "x-usage-examples": Array<{ definition: Record<string, unknown> }>;
        };
        const sourceSections = authoringHelpSections.filter((section) => section.parentId === "output-data");
        const sourceYamlExamples = sourceSections.map((section) => section.body.match(/```yaml\n([\s\S]+?)\n```/)?.[1]);

        expect(sourceSections.map((section) => section.id)).toEqual([
            "output-data-format-source",
            "output-data-metadata-source",
        ]);
        expect(sourceSections.map((section) => section.title)).toEqual(["format_source", "metadata_source"]);
        expect(parse(sourceYamlExamples[0]!)).toEqual(dataOutputDefinition["x-usage-examples"][0]?.definition);
        expect(parse(sourceYamlExamples[1]!)).toEqual(dataOutputDefinition["x-usage-examples"][1]?.definition);
        expect(dataOutput?.body).toContain("[`format_source` #](#output-data-format-source)");
        expect(dataOutput?.body).toContain("[`metadata_source` #](#output-data-metadata-source)");
        expect(sourceSections[0]?.body).toMatch(/^`format_source` can be used to assign/);
        expect(sourceSections[1]?.body).toMatch(/^`metadata_source` can be used to copy/);
        expect(sourceSections[0]?.body).toContain("format_source: reads");
        expect(sourceSections[1]?.body).toContain("metadata_source: intervals");
        expect(sourceSections.every((section) => section.body.includes("inputs:"))).toBe(true);
        expect(sourceSections.every((section) => section.body.includes("shell_command:"))).toBe(true);
        expect(dataOutput?.body).toContain("filtering reads");
        expect(dataOutput?.body).toContain("interval column assignments");
    });

    it("builds one navigable reference entry per validator schema example", () => {
        const definitions = TOOL_SOURCE_SCHEMA.$defs as Record<
            string,
            {
                examples?: Array<Record<string, unknown>>;
                properties?: { type?: { const?: string } };
            }
        >;
        const validatorDefinitions = Object.entries(definitions).filter(([name]) =>
            name.endsWith("ParameterValidatorModel"),
        );
        const validatorSections = authoringHelpSections.filter(
            (section) => section.parentId === "validator-types-reference",
        );
        const validatorIndex = authoringHelpSections.find((section) => section.id === "validators");

        expect(validatorSections.map((section) => section.id)).toEqual(
            validatorDefinitions.map(([, definition]) => `validator-${definition.properties?.type?.const}`),
        );
        for (const section of validatorSections) {
            const validatorType = section.id.replace("validator-", "");
            const definition = validatorDefinitions.find(
                ([, definition]) => definition.properties?.type?.const === validatorType,
            )?.[1];
            const yamlExample = section.body.match(/```yaml\n([\s\S]+?)\n```/)?.[1];

            expect(definition?.examples).toHaveLength(1);
            expect(validatorIndex?.body).toContain(`](#${section.id})`);
            expect(validatorIndex?.body).toContain(`\` #](#${section.id})`);
            expect(section.kind).toBe("detailed-reference");
            expect(section.parentId).toBe("validator-types-reference");
            expect(parse(yamlExample!).validators[0]).toEqual(definition?.examples?.[0]);
        }
    });

    it("resolves Galaxy documentation links for the editor", () => {
        const input = "[Tool schema](gxdoc:dev/schema.md) and [Datatypes](gxui:/datatypes)";

        expect(resolveDocLinks(input)).toBe(
            "[Tool schema](https://docs.galaxyproject.org/en/master/dev/schema.html) and [Datatypes](/datatypes)",
        );
    });

    it("links schema keys outside code fences", () => {
        const input = [
            "Use `shell_command` with [`inputs`](#parameters).",
            "",
            "```yaml",
            "shell_command: echo ok",
            "```",
        ].join("\n");

        expect(linkSchemaKeys(input)).toBe(
            [
                "Use [`shell_command` #](#expressions) with [`inputs` #](#parameters).",
                "",
                "```yaml",
                "shell_command: echo ok",
                "```",
            ].join("\n"),
        );
    });

    it("does not leave unresolved documentation links in rendered content", () => {
        expect(authoringHelpIntro).not.toContain("gxdoc:");
        for (const section of authoringHelpSections) {
            expect(section.body).not.toContain("gxdoc:");
            expect(section.body).not.toContain("gxui:");
        }
    });

    it("links discovery guidance and the current instance datatype page", () => {
        const outputs = authoringHelpSections.find((section) => section.id === "outputs");
        const discovery = authoringHelpSections.find((section) => section.id === "discover-datasets");
        const dataParameter = authoringHelpSections.find((section) => section.id === "parameter-data");

        expect(outputs?.body).toContain("[`discover_datasets` #](#discover-datasets)");
        expect(discovery?.parentId).toBeUndefined();
        const detailedReference = authoringHelpGroups.find((group) => group.id === "detailed-reference")?.sections;
        expect(detailedReference?.filter((section) => !section.parentId).map((section) => section.id)).toEqual([
            "parameter-types-reference",
            "validator-types-reference",
            "output-types-reference",
            "discover-datasets",
        ]);
        expect(discovery?.body).toContain("[Datatypes page](/datatypes)");
        expect(discovery?.body).toContain("matching filenames");
        expect(discovery?.body).not.toContain("tool-provided metadata");
        expect(discovery?.body).not.toContain("galaxy.json");
        expect(dataParameter?.body).toContain("Accepted Galaxy datatype extensions");
        expect(authoringHelpSections.find((section) => section.id === "parameters")?.body).toContain(
            "[Datatypes page](/datatypes)",
        );
    });

    it("recognizes embedded authoring-reference links", () => {
        expect(linkedAuthoringHelpSection("https://schema.galaxyproject.org/customTool.json")).toBe("tool-format");
        expect(linkedAuthoringHelpSection("#outputs")).toBe("outputs");
        expect(linkedAuthoringHelpSection("authoring-help#parameter-data")).toBe("parameter-data");
        expect(linkedAuthoringHelpSection("/authoring-help#output-collection")).toBe("output-collection");
        expect(linkedAuthoringHelpSection("#missing")).toBeUndefined();
        expect(linkedAuthoringHelpSection("https://example.org/#outputs")).toBeUndefined();
    });
});
