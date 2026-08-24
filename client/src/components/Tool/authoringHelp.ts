import RAW_AUTHORING_HELP from "./authoringHelp.yml";
import { buildOutputTypeReference, buildParameterTypeReference } from "./authoringHelpTypes";
import { TOOL_SOURCE_SCHEMA_URI } from "./schemaMarkdown";

/** Editor adapter for the shared guidance in `authoringHelp.yml`. */

export interface AuthoringHelpSection {
    id: string;
    title: string;
    kind: "reference" | "faq";
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
    sections: Array<AuthoringHelpSection & { output_types?: boolean; parameter_types?: boolean }>;
}

const HELP = RAW_AUTHORING_HELP as RawAuthoringHelp;

const DOCS_BASE = "https://docs.galaxyproject.org/en/master/";

// Bodies reference other Galaxy documentation pages by source path, as
// `[text](gxdoc:dev/schema.md)`, so the same string can resolve to a relative
// path in the generated Sphinx page and to an absolute URL here.
const GXDOC_LINK = /\]\(gxdoc:([^)]+)\)/g;
const OUTPUT_TYPE_INDEX = "{{output_type_index}}";
const PARAMETER_TYPE_INDEX = "{{parameter_type_index}}";

export function resolveDocLinks(text: string): string {
    return text.replace(GXDOC_LINK, (_match, target: string) => {
        return `](${DOCS_BASE}${target.replace(/\.(md|rst)$/, ".html")})`;
    });
}

export const authoringHelpTitle: string = HELP.title;

export const authoringHelpIntro: string = resolveDocLinks(HELP.intro);

const parameterTypeReference = buildParameterTypeReference();
const outputTypeReference = buildOutputTypeReference();

export const authoringHelpSections: AuthoringHelpSection[] = HELP.sections.flatMap((rawSection) => {
    const { output_types: hasOutputTypes, parameter_types: hasParameterTypes, ...section } = rawSection;
    const resolvedSection = {
        ...section,
        body: resolveDocLinks(section.body)
            .replace(PARAMETER_TYPE_INDEX, parameterTypeReference.index)
            .replace(OUTPUT_TYPE_INDEX, outputTypeReference.index),
    };
    const nestedSections = [
        ...(hasParameterTypes ? parameterTypeReference.sections : []),
        ...(hasOutputTypes ? outputTypeReference.sections : []),
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
        id: "reference",
        title: "Reference",
        sections: authoringHelpSections.filter((section) => section.kind === "reference"),
    },
    {
        id: "faq",
        title: "Common questions",
        sections: authoringHelpSections.filter((section) => section.kind === "faq"),
    },
];
