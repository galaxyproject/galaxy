const FUNCTION_VALUE_REGEX = `\\s*(?:[\\w_\\-]+|\\"[^\\"]+\\"|\\'[^\\']+\\')\\s*`;
const FUNCTION_CALL = `\\s*[\\w\\|]+\\s*=` + FUNCTION_VALUE_REGEX;
const FUNCTION_CALL_LINE = `\\s*(\\w+)\\s*\\(\\s*(?:(${FUNCTION_CALL})(,${FUNCTION_CALL})*)?\\s*\\)\\s*`;
const FUNCTION_CALL_LINE_TEMPLATE = new RegExp(FUNCTION_CALL_LINE, "m");

export function splitMarkdown(markdown: string) {
    const sections = [];
    const markdownErrors = [];
    let digest = markdown;
    while (digest.length > 0) {
        const galaxyStart = digest.indexOf("```galaxy");
        if (galaxyStart != -1) {
            const galaxyEnd = digest.substr(galaxyStart + 1).indexOf("```");
            if (galaxyEnd != -1) {
                if (galaxyStart > 0) {
                    const defaultContent = digest.substr(0, galaxyStart).trim();
                    if (defaultContent) {
                        sections.push({
                            name: "default",
                            content: defaultContent,
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

export function getArgs(content: string) {
    const galaxy_function = FUNCTION_CALL_LINE_TEMPLATE.exec(content);
    if (galaxy_function == null) {
        throw Error("Failed to parse galaxy directive");
    }
    type ArgsType = { [key: string]: string };
    const args: ArgsType = {};
    const function_name = galaxy_function[1];
    // we need [... ] to return empty string, if regex doesn't match
    const function_arguments = [...content.matchAll(new RegExp(FUNCTION_CALL, "g"))];
    for (let i = 0; i < function_arguments.length; i++) {
        if (function_arguments[i] === undefined) {
            continue;
        }
        const arguments_str = function_arguments[i]?.toString().replace(/,/g, "").trim();
        if (arguments_str) {
            const [key, val] = arguments_str.split("=");
            if (key == undefined || val == undefined) {
                throw Error("Failed to parse galaxy directive");
            }
            args[key.trim()] = val.replace(/['"]+/g, "").trim();
        }
    }
    return {
        name: function_name,
        args: args,
        content: content,
    };
}
