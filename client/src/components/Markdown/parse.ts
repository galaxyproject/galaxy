import { parseBlockContent } from "./Utilities/blockContent";

const FUNCTION_ARGUMENT_VALUE_REGEX = `\\s*(?:[\\w_\\-]+|\\"[^\\"]+\\"|\\'[^\\']+\\')\\s*`;
const FUNCTION_ARGUMENT_VALUE_TO_VALUE_REGEX = `\\s*(?:\\"(?<unquoted>[^\\"]+)\\"|\\'(?<squoted>[^\\']+)\\'|(?<dquoted>[\\w_\\-]+))\\s*`;
const FUNCTION_ARGUMENT_REGEX = `\\s*[\\w\\|]+\\s*=` + FUNCTION_ARGUMENT_VALUE_REGEX;
const FUNCTION_CALL_LINE = `\\s*(\\w+)\\s*\\(\\s*(?:(${FUNCTION_ARGUMENT_REGEX})(,${FUNCTION_ARGUMENT_REGEX})*)?\\s*\\)\\s*`;
const FUNCTION_CALL_LINE_TEMPLATE = new RegExp(FUNCTION_CALL_LINE, "m");

type DefaultSection = { name: "markdown"; content: string };
type GalaxySection = { name: string; content: string; args: { [key: string]: string } };
type Section = DefaultSection | GalaxySection;

type WorkflowLabelKind = "input" | "output" | "step";

const SINGLE_QUOTE = "'";
const DOUBLE_QUOTE = '"';

function parseResult(result: { name: string; content: string }[], name: string, content: string[]) {
    const trimmedContent = content.join("\n").trim();
    if (trimmedContent.length > 0) {
        result.push({ name: name, content: trimmedContent });
    }
}

export function parseMarkdown(input: string): { name: string; content: string }[] {
    const result: { name: string; content: string }[] = [];
    const lines = input.split("\n");
    let currentName: string = "markdown";
    let currentContent: string[] = [];
    lines.forEach((line) => {
        const sectionMatch = line.trim().match(/^```(.*)$/);
        if (sectionMatch) {
            parseResult(result, currentName, currentContent);
            currentName = sectionMatch[1] || "markdown";
            currentContent = [];
        } else {
            currentContent.push(line);
        }
    });
    parseResult(result, currentName, currentContent);
    return result;
}

/**
 * Whitespace-preserving scanner used by {@link replaceLabel} to rewrite label
 * arguments in place. Recognizes only ```galaxy directive blocks; visualization
 * / vega / vitessce config blocks are handled by parseMarkdown + parseBlockContent
 * elsewhere. The `+ 4` spans the closing fence: the search for the closing ```
 * starts at galaxyStart + 1, so the block ends at galaxyStart + galaxyEnd + 1 + 3.
 */
export function splitMarkdown(markdown: string, preserveWhitespace = false) {
    const sections: Section[] = [];
    const markdownErrors = [];
    let digest = markdown;
    while (digest.length > 0) {
        const galaxyStart = digest.indexOf("```galaxy");
        if (galaxyStart != -1) {
            const galaxyEnd = digest.substr(galaxyStart + 1).indexOf("```");
            if (galaxyEnd != -1) {
                if (galaxyStart > 0) {
                    const rawContent = digest.substr(0, galaxyStart);
                    const defaultContent = rawContent.trim();
                    if (preserveWhitespace || defaultContent) {
                        sections.push({
                            name: "markdown",
                            content: preserveWhitespace ? rawContent : defaultContent,
                        });
                    }
                }
                const galaxyEndIndex = galaxyEnd + 4;
                const galaxySection = digest.substr(galaxyStart, galaxyEndIndex);
                let args = null;
                try {
                    args = getArgs(galaxySection);
                    sections.push(args);
                } catch (e) {
                    markdownErrors.push({
                        error: "Found an unresolved tag.",
                        line: galaxySection,
                    });
                }
                digest = digest.substr(galaxyStart + galaxyEndIndex);
            } else {
                digest = digest.substr(galaxyStart + 1);
            }
        } else {
            sections.push({
                name: "markdown",
                content: digest,
            });
            break;
        }
    }
    return { sections, markdownErrors };
}

export function replaceLabel(
    markdown: string,
    labelType: WorkflowLabelKind,
    fromLabel: string | null | undefined,
    toLabel: string | null | undefined,
): string {
    const { sections } = splitMarkdown(markdown, true);

    function rewriteSection(section: Section) {
        if ("args" in section) {
            const directiveSection = section as GalaxySection;
            const args = directiveSection.args;
            if (!(labelType in args)) {
                return section;
            }
            const labelValue = args[labelType];
            if (labelValue != fromLabel) {
                return section;
            }
            // we've got a section with a matching label and type...
            const newArgs = { ...args };
            newArgs[labelType] = toLabel ?? "";
            const argRexExp = namedArgumentRegex(labelType);
            let escapedToLabel = escapeRegExpReplacement(toLabel ?? "");
            const incomingContent = directiveSection.content;
            let content: string;
            const match = incomingContent.match(argRexExp);
            if (match) {
                const firstMatch = match[0];
                // TODO: handle whitespace more broadly here...
                if (escapedToLabel.indexOf(" ") >= 0) {
                    const quoteChar = getQuoteChar(firstMatch);
                    escapedToLabel = `${quoteChar}${escapedToLabel}${quoteChar}`;
                }
                content = incomingContent.replace(argRexExp, `$1${escapedToLabel}`);
            } else {
                content = incomingContent;
            }
            return {
                name: directiveSection.name,
                args: newArgs,
                content: content,
            };
        } else {
            return section;
        }
    }

    const rewrittenSections = sections.map(rewriteSection);
    const rewrittenMarkdown = rewrittenSections.map((section) => section.content).join("");
    return rewrittenMarkdown;
}

function getQuoteChar(argMatch: string): string {
    // this could be a lot stronger, handling escaping and such...
    let quoteChar = SINGLE_QUOTE;
    if (argMatch.indexOf(DOUBLE_QUOTE) >= 0) {
        quoteChar = DOUBLE_QUOTE;
    }
    return quoteChar;
}

export function getArgs(content: string): GalaxySection {
    const galaxy_function = FUNCTION_CALL_LINE_TEMPLATE.exec(content);
    if (galaxy_function == null) {
        throw Error("Failed to parse galaxy directive");
    }
    type ArgsType = { [key: string]: string };
    const args: ArgsType = {};
    const function_name = galaxy_function[1] as string;
    // we need [... ] to return empty string, if regex doesn't match
    const function_arguments = [...content.matchAll(new RegExp(FUNCTION_ARGUMENT_REGEX, "g"))];
    for (let i = 0; i < function_arguments.length; i++) {
        const arguments_str = function_arguments[i]?.toString().trim();
        if (arguments_str) {
            // Split on the first "=" only, so commas and "=" inside a quoted
            // value survive (e.g. title="a, b" or expr="a=b").
            const eqIndex = arguments_str.indexOf("=");
            if (eqIndex === -1) {
                throw Error("Failed to parse galaxy directive");
            }
            const key = arguments_str.slice(0, eqIndex).trim();
            let val: string = arguments_str.slice(eqIndex + 1).trim();
            if (!key) {
                throw Error("Failed to parse galaxy directive");
            }
            if (val) {
                const strippedValueMatch = val.match(FUNCTION_ARGUMENT_VALUE_TO_VALUE_REGEX);
                const groups = strippedValueMatch?.groups;
                if (groups) {
                    val = groups.unquoted ?? groups.squoted ?? groups.dquoted ?? val;
                }
            }
            args[key] = val;
        }
    }
    return {
        name: function_name,
        args: args,
        content: content,
    };
}

function namedArgumentRegex(argument: string): RegExp {
    return new RegExp(`(\\s*${argument}\\s*=)` + FUNCTION_ARGUMENT_VALUE_REGEX);
}

// https://stackoverflow.com/questions/3446170/escape-string-for-use-in-javascript-regex
function escapeRegExpReplacement(value: string): string {
    return value.replace(/\$/g, "$$$$");
}

class ReferencedObjects {
    jobs: Set<string> = new Set();
    historyDatasets: Set<string> = new Set();
    historyDatasetCollections: Set<string> = new Set();
    workflows: Set<string> = new Set();
    invocations: Set<string> = new Set();
}

// Recursively collect dataset/collection/invocation references from a parsed
// config block (visualization, vega, vitessce). Keys are matched by name so
// nested shapes (tracks[], datasets[].files[].__gx_dataset_id, dataset_label)
// are all covered.
function collectReferencesFromConfig(value: unknown, objects: ReferencedObjects): void {
    if (Array.isArray(value)) {
        for (const entry of value) {
            collectReferencesFromConfig(entry, objects);
        }
    } else if (value !== null && typeof value === "object") {
        for (const [key, entry] of Object.entries(value as Record<string, unknown>)) {
            if (typeof entry === "string") {
                if (key === "dataset_id" || key === "__gx_dataset_id") {
                    addToSetIfHasValue(entry, objects.historyDatasets);
                } else if (key === "history_dataset_collection_id") {
                    addToSetIfHasValue(entry, objects.historyDatasetCollections);
                } else if (key === "invocation_id") {
                    addToSetIfHasValue(entry, objects.invocations);
                }
            } else {
                collectReferencesFromConfig(entry, objects);
            }
        }
    }
}

export function referencedObjects(markdown: string) {
    const objects = new ReferencedObjects();
    // Walk every fenced block, not just ```galaxy: directive args and the
    // dataset bindings inside visualization/vega/vitessce config blocks both
    // count as references (e.g. so ObjectPermissions grants access to them).
    for (const section of parseMarkdown(markdown)) {
        if (section.name === "markdown") {
            continue;
        }
        if (section.name === "galaxy") {
            let directive: GalaxySection;
            try {
                directive = getArgs(section.content);
            } catch {
                continue;
            }
            const args = directive.args;
            addToSetIfHasValue(args.job_id, objects.jobs);
            addToSetIfHasValue(args.history_dataset_id, objects.historyDatasets);
            addToSetIfHasValue(args.history_dataset_collection_id, objects.historyDatasetCollections);
            addToSetIfHasValue(args.invocation_id, objects.invocations);
            addToSetIfHasValue(args.workflow_id, objects.workflows);
        } else {
            try {
                collectReferencesFromConfig(parseBlockContent(section.content), objects);
            } catch {
                // non-structured or unparseable block: nothing to reference
            }
        }
    }
    return objects;
}

function addToSetIfHasValue(value: string | undefined, toSet: Set<string>): void {
    if (value) {
        toSet.add(value);
    }
}
