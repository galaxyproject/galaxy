import type { Invocation } from "@/components/Markdown/Editor/types";

import { parseInput, parseOutput } from "./parseInvocation";

// Pattern to match inline Galaxy directives: ${galaxy directive_name(args)}
const INLINE_DIRECTIVE_PATTERN = /\$\{galaxy\s+(\w+)\s*\((.*?)\)\s*\}/g;

// Pattern to extract key=value pairs from directive arguments
const ARG_PATTERN = /(\w+)\s*=\s*(?:"([^"]+)"|'([^']+)'|(\S+?))\s*(?:,|$)/g;

interface DirectiveArgs {
    [key: string]: string;
}

function parseDirectiveArgs(argsString: string): DirectiveArgs {
    const args: DirectiveArgs = {};
    let match;
    // Need to reset lastIndex when reusing the regex
    ARG_PATTERN.lastIndex = 0;
    while ((match = ARG_PATTERN.exec(argsString)) !== null) {
        const key = match[1];
        const value = match[2] || match[3] || match[4];
        if (key && value) {
            args[key] = value;
        }
    }
    return args;
}

/**
 * Resolves inline Galaxy directives in markdown content using invocation data.
 *
 * For directives like `${galaxy history_dataset_as_image(invocation_id=abc, output=my_output)}`,
 * this function resolves the output label to an actual dataset ID using the invocation data,
 * and returns the markdown with the directive converted to an image reference.
 *
 * @param content The markdown content containing inline directives
 * @param getInvocationById Function to retrieve invocation data by ID
 * @returns The processed markdown with resolved inline directives
 */
export function resolveInlineDirectives(
    content: string,
    // Using a permissive type to work with both Invocation and WorkflowInvocation
    getInvocationById: (id: string) => Invocation | Record<string, unknown> | null | undefined,
): string {
    return content.replace(INLINE_DIRECTIVE_PATTERN, (match, directiveName, argsString) => {
        const args = parseDirectiveArgs(argsString);

        // If there's an invocation_id, try to resolve labels
        if (args.invocation_id) {
            const invocation = getInvocationById(args.invocation_id);
            if (invocation) {
                // Cast to Invocation type for parseInput/parseOutput
                // These functions expect specific properties that WorkflowInvocation also has
                const inv = invocation as Invocation;
                // Resolve input or output labels
                let datasetId: string | undefined;
                if (args.output) {
                    datasetId = parseOutput(inv, args.output);
                } else if (args.input) {
                    datasetId = parseInput(inv, args.input);
                }

                // If we resolved a dataset ID, expand the directive
                if (datasetId) {
                    if (directiveName === "history_dataset_as_image") {
                        const name = args.output || args.input || "Image";
                        return `![${name}](gxdatasetasimage://${datasetId})`;
                    }
                    // For other directives, keep the original but with resolved ID
                    // This ensures other inline directives can be handled similarly
                }
            }
        }

        // If we couldn't resolve, return the original match
        // This allows unresolved directives to be visible for debugging
        return match;
    });
}

/**
 * Extracts all invocation IDs from inline directives in the content.
 * This is useful for pre-fetching invocation data before resolving.
 *
 * @param content The markdown content to scan for invocation IDs
 * @returns Array of unique invocation IDs found in inline directives
 */
export function extractInvocationIds(content: string): string[] {
    const ids = new Set<string>();
    let match;
    const pattern = new RegExp(INLINE_DIRECTIVE_PATTERN.source, "g");
    while ((match = pattern.exec(content)) !== null) {
        const args = parseDirectiveArgs(match[2] || "");
        if (args.invocation_id) {
            ids.add(args.invocation_id);
        }
    }
    return Array.from(ids);
}
