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
        expect(authoringHelpGroups.map((group) => group.title)).toEqual(["Reference", "Common questions"]);
        expect(authoringHelpGroups.every((group) => group.sections.length > 0)).toBe(true);
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
        const parameterSections = authoringHelpSections.filter((section) => section.id.startsWith("parameter-"));
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
            expect(section.parentId).toBe("parameters");
            expect(yamlExamples).toHaveLength(2);
            expect(section.body).toContain(`Add this \`${parameterType}\` parameter under \`inputs\``);
            expect(parse(inputExample!).inputs[0]).toEqual(definition.examples[0]);
            expect(parse(shellCommandExample!).shell_command.trim()).toBe(definition["x-shell-command"]);
        }
    });

    it("builds one navigable reference entry per output schema example", () => {
        const definitions = TOOL_SOURCE_SCHEMA.$defs as Record<string, unknown>;
        const mapping = TOOL_SOURCE_SCHEMA.properties.outputs.items.discriminator.mapping;
        const outputSections = authoringHelpSections.filter((section) => section.id.startsWith("output-"));
        const outputIndex = authoringHelpSections.find((section) => section.id === "outputs");

        expect(outputSections.map((section) => section.id)).toEqual(
            Object.keys(mapping).map((outputType) => `output-${outputType}`),
        );
        for (const section of outputSections) {
            const outputType = section.id.replace("output-", "");
            const definitionName = mapping[outputType as keyof typeof mapping].split("/").at(-1)!;
            const definition = definitions[definitionName] as { examples: Array<Record<string, unknown>> };
            const yamlExample = section.body.match(/```yaml\n([\s\S]+?)\n```/)?.[1];

            expect(outputIndex?.body).toContain(`](#${section.id})`);
            expect(section.parentId).toBe("outputs");
            expect(section.body).toContain(`Add this \`${outputType}\` output under \`outputs\``);
            expect(parse(yamlExample!).outputs[0]).toEqual(definition.examples[0]);
        }
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
        const validatorSections = authoringHelpSections.filter((section) => section.id.startsWith("validator-"));
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
            expect(section.parentId).toBe("validators");
            expect(parse(yamlExample!).validators[0]).toEqual(definition?.examples?.[0]);
        }
    });

    it("resolves Galaxy documentation links for the editor", () => {
        const input = "[Tool schema](gxdoc:dev/schema.md)";

        expect(resolveDocLinks(input)).toBe("[Tool schema](https://docs.galaxyproject.org/en/master/dev/schema.html)");
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
        }
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
