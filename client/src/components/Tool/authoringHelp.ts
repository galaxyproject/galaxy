import RAW_AUTHORING_HELP from "./authoringHelp.yml";

/** Editor adapter for the shared guidance in `authoringHelp.yml`. */

export interface AuthoringHelpSection {
    id: string;
    title: string;
    kind: "reference" | "faq";
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
    sections: AuthoringHelpSection[];
}

const HELP = RAW_AUTHORING_HELP as RawAuthoringHelp;

const DOCS_BASE = "https://docs.galaxyproject.org/en/master/";

// Bodies reference other Galaxy documentation pages by source path, as
// `[text](gxdoc:dev/schema.md)`, so the same string can resolve to a relative
// path in the generated Sphinx page and to an absolute URL here.
const GXDOC_LINK = /\]\(gxdoc:([^)]+)\)/g;

export function resolveDocLinks(text: string): string {
    return text.replace(GXDOC_LINK, (_match, target: string) => {
        return `](${DOCS_BASE}${target.replace(/\.(md|rst)$/, ".html")})`;
    });
}

export const authoringHelpTitle: string = HELP.title;

export const authoringHelpIntro: string = resolveDocLinks(HELP.intro);

export const authoringHelpSections: AuthoringHelpSection[] = HELP.sections.map((section) => ({
    ...section,
    body: resolveDocLinks(section.body),
}));

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
