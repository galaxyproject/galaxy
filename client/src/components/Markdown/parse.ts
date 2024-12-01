const FUNCTION_ARGUMENT_VALUE_REGEX = `\\s*(?:[\\w_\\-]+|\\"[^\\"]+\\"|\\'[^\\']+\\')\\s*`;
const FUNCTION_ARGUMENT_VALUE_TO_VALUE_REGEX = `\\s*(?:\\"(?<unquoted>[^\\"]+)\\"|\\'(?<squoted>[^\\']+)\\'|(?<dquoted>[\\w_\\-]+))\\s*`;
const FUNCTION_ARGUMENT_REGEX = `\\s*[\\w\\|]+\\s*=` + FUNCTION_ARGUMENT_VALUE_REGEX;
const FUNCTION_CALL_LINE = `\\s*(\\w+)\\s*\\(\\s*(?:(${FUNCTION_ARGUMENT_REGEX})(,${FUNCTION_ARGUMENT_REGEX})*)?\\s*\\)\\s*`;
const FUNCTION_CALL_LINE_TEMPLATE = new RegExp(FUNCTION_CALL_LINE, "m");

type DefaultSection = { name: "default"; content: string };
type GalaxyDirectiveSection = { name: string; content: string; args: { [key: string]: string } };
type Section = DefaultSection | GalaxyDirectiveSection;

type WorkflowLabelKind = "input" | "output" | "step";

const SINGLE_QUOTE = "'";
const DOUBLE_QUOTE = '"';

export function parseSections(input: string): { name: string; content: string }[] {
    const result: { name: string; content: string }[] = [];
    const lines = input.split("\n");
    let currentName: string = "default";
    let currentContent: string[] = [];
    lines.forEach((line) => {
        const sectionMatch = line.match(/^```(.*)$/);
        if (sectionMatch) {
            console.log(sectionMatch);
            if (currentContent.length > 0) {
                result.push({ name: currentName, content: currentContent.join("\n").trim() });
            }
            currentName = sectionMatch[1] || "default";
            currentContent = [];
        } else {
            currentContent.push(line);
        }
    });
    if (currentContent.length > 0) {
        result.push({ name: currentName, content: currentContent.join("\n").trim() });
    }
    return result;
}

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
                            name: "default",
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
                name: "default",
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
    toLabel: string | null | undefined
): string {
    const { sections } = splitMarkdown(markdown, true);

    function rewriteSection(section: Section) {
        if ("args" in section) {
            const directiveSection = section as GalaxyDirectiveSection;
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

export function getArgs(content: string): GalaxyDirectiveSection {
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
        if (function_arguments[i] === undefined) {
            continue;
        }
        const arguments_str = function_arguments[i]?.toString().replace(/,/g, "").trim();
        if (arguments_str) {
            const [keyStr, valStr] = arguments_str.split("=");
            if (keyStr == undefined || valStr == undefined) {
                throw Error("Failed to parse galaxy directive");
            }
            const key = keyStr.trim();
            let val: string = valStr?.trim() ?? "";
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

export function referencedObjects(markdown: string) {
    const { sections } = splitMarkdown(markdown);
    const objects = new ReferencedObjects();
    for (const section of sections) {
        if (!("args" in section)) {
            continue;
        }
        const args = section.args;
        if (!args) {
            continue;
        }
        if ("job_id" in args) {
            addToSetIfHasValue(args.job_id, objects.jobs);
        }
        if ("history_dataset_id" in args) {
            addToSetIfHasValue(args.history_dataset_id, objects.historyDatasets);
        }
        if ("history_dataset_collection_id" in args) {
            addToSetIfHasValue(args.history_dataset_collection_id, objects.historyDatasetCollections);
        }
        if ("invocation_id" in args) {
            addToSetIfHasValue(args.invocation_id, objects.invocations);
        }
        if ("workflow_id" in args) {
            addToSetIfHasValue(args.workflow_id, objects.workflows);
        }
        // TODO: implicit collect job ids
    }
    return objects;
}

function addToSetIfHasValue(value: string | undefined, toSet: Set<string>): void {
    if (value) {
        toSet.add(value);
    }
}
