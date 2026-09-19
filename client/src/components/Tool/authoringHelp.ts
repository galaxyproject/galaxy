import RAW_AUTHORING_HELP from "./authoringHelp.yml";
import {
    buildOutputTypeReference,
    buildParameterTypeReference,
    buildQuickStartExample,
    buildValidatorTypeReference,
} from "./authoringHelpTypes";
import { TOOL_SOURCE_SCHEMA_URI } from "./schemaMarkdown";

/** Editor adapter for the shared guidance in `authoringHelp.yml`. */

export interface AuthoringHelpSection {
    id: string;
    title: string;
    kind: "getting-started" | "reference" | "detailed-reference" | "faq";
    parentId?: string;
    body: string;
}

export interface AuthoringHelpGroup {
    id: AuthoringHelpSection["kind"];
    title: string;
    sections: AuthoringHelpSection[];
}

interface RawAuthoringHelp {
    title: string;
    intro: string;
    sections: Array<
        AuthoringHelpSection & { output_types?: boolean; parameter_types?: boolean; validator_types?: boolean }
    >;
}

const HELP = RAW_AUTHORING_HELP as RawAuthoringHelp;

const DOCS_BASE = "https://docs.galaxyproject.org/en/master/";

// Bodies reference other Galaxy documentation pages by source path, as
// `[text](gxdoc:dev/schema.md)`, so the same string can resolve to a relative
// path in the generated Sphinx page and to an absolute URL here.
const GXDOC_LINK = /\]\(gxdoc:([^)]+)\)/g;
const GXUI_LINK = /\]\(gxui:([^)]+)\)/g;
const QUICK_START_EXAMPLE = "{{quick_start_example}}";
const OUTPUT_TYPE_INDEX = "{{output_type_index}}";
const PARAMETER_TYPE_INDEX = "{{parameter_type_index}}";
const VALIDATOR_TYPE_INDEX = "{{validator_type_index}}";
const SCHEMA_KEY_SECTIONS: Record<string, string> = {
    class: "tool-format",
    container: "containers-reference",
    shell_command: "expressions",
    configfiles: "configfiles",
    inputs: "parameters",
    outputs: "outputs",
    requirements: "resource-requirements",
    validators: "validators",
    discover_datasets: "discover-datasets",
    help: "help-content",
    tests: "testing",
    citations: "citations-metadata",
    license: "citations-metadata",
    profile: "tool-format",
    edam_operations: "citations-metadata",
    edam_topics: "citations-metadata",
    xrefs: "citations-metadata",
};
const LINKED_SCHEMA_KEY = /\[`([a-z_]+)`\]\(#[^)]+\)/g;
const INLINE_SCHEMA_KEY = /`([a-z_]+)`/g;

export function resolveDocLinks(text: string): string {
    return text
        .replace(GXDOC_LINK, (_match, target: string) => {
            return `](${DOCS_BASE}${target.replace(/\.(md|rst)$/, ".html")})`;
        })
        .replace(GXUI_LINK, (_match, target: string) => `](${target})`);
}

export function linkSchemaKeys(text: string): string {
    let inFence = false;
    return text
        .split("\n")
        .map((line) => {
            if (line.trimStart().startsWith("```")) {
                inFence = !inFence;
                return line;
            }
            if (inFence) {
                return line;
            }
            const markedLinks = line.replace(LINKED_SCHEMA_KEY, (match, key: string) => {
                return SCHEMA_KEY_SECTIONS[key] ? match.replace("`]", "` #]") : match;
            });
            return markedLinks.replace(INLINE_SCHEMA_KEY, (match, key: string, offset: number, source: string) => {
                const section = SCHEMA_KEY_SECTIONS[key];
                const alreadyLinked =
                    source[offset - 1] === "[" || source.slice(offset + match.length).startsWith(" #](");
                return section && !alreadyLinked ? `[\`${key}\` #](#${section})` : match;
            });
        })
        .join("\n");
}

export const authoringHelpTitle: string = HELP.title;

export const authoringHelpIntro: string = linkSchemaKeys(resolveDocLinks(HELP.intro));

const parameterTypeReference = buildParameterTypeReference();
const outputTypeReference = buildOutputTypeReference();
const validatorTypeReference = buildValidatorTypeReference();
const quickStartExample = buildQuickStartExample();

export const authoringHelpSections: AuthoringHelpSection[] = HELP.sections.flatMap((rawSection) => {
    const {
        output_types: hasOutputTypes,
        parameter_types: hasParameterTypes,
        validator_types: hasValidatorTypes,
        ...section
    } = rawSection;
    const resolvedSection = {
        ...section,
        body: linkSchemaKeys(
            resolveDocLinks(section.body)
                .replace(QUICK_START_EXAMPLE, quickStartExample)
                .replace(PARAMETER_TYPE_INDEX, parameterTypeReference.index)
                .replace(OUTPUT_TYPE_INDEX, outputTypeReference.index)
                .replace(VALIDATOR_TYPE_INDEX, validatorTypeReference.index),
        ),
    };
    const nestedSections = [
        ...(hasParameterTypes ? parameterTypeReference.sections : []),
        ...(hasOutputTypes ? outputTypeReference.sections : []),
        ...(hasValidatorTypes ? validatorTypeReference.sections : []),
    ];
    return [resolvedSection, ...nestedSections];
});

const authoringHelpSectionIds = new Set(authoringHelpSections.map((section) => section.id));

export function linkedAuthoringHelpSection(href: string): string | undefined {
    if (href === TOOL_SOURCE_SCHEMA_URI) {
        return "tool-format";
    }
    if (!href.startsWith("#") && !href.includes("authoring-help#")) {
        return undefined;
    }
    const hash = href.slice(href.indexOf("#") + 1);
    const sectionId = decodeURIComponent(hash);
    return authoringHelpSectionIds.has(sectionId) ? sectionId : undefined;
}

export const authoringHelpGroups: AuthoringHelpGroup[] = [
    {
        id: "getting-started",
        title: "Getting Started",
        sections: authoringHelpSections.filter((section) => section.kind === "getting-started"),
    },
    {
        id: "reference",
        title: "Reference",
        sections: authoringHelpSections.filter((section) => section.kind === "reference"),
    },
    {
        id: "detailed-reference",
        title: "Detailed reference",
        sections: authoringHelpSections.filter((section) => section.kind === "detailed-reference"),
    },
    {
        id: "faq",
        title: "Common questions",
        sections: authoringHelpSections.filter((section) => section.kind === "faq"),
    },
];
