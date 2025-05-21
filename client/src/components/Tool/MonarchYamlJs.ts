import type { languages } from "monaco-editor/esm/vs/editor/editor.api";

// The actual IMonarchLanguageBracket shape doesn't work at runtime ...
const brackets = [
    ["{", "}", "delimiter.curly"],
    ["$(", ")", "delimiter.parenthesis"],
    ["[", "]", "delimiter.square"],
    ["(", ")", "delimiter.parenthesis"],
    ["<", ">", "delimiter.angle"],
] as any as languages.IMonarchLanguageBracket[];

export const monarchConfig: languages.IMonarchLanguage = {
    brackets: brackets,
    tokenizer: {
        root: [
            [
                /(requirements)(:)(\s*)/,
                [
                    { token: "type.yaml", next: "@requirements", log: "requirements" },
                    "operators.yaml",
                    "whitespace.yaml",
                ],
            ],
            [
                /(shell_command)(:)(\s*)(\|)/,
                [{ token: "type.yaml", next: "@shellCommand" }, "operators.yaml", "whitespace.yaml", "operators.yaml"],
            ],
            [
                /(shell_command)(:)(\s*)/,
                [{ token: "type.yaml", next: "@shellCommand" }, "operator.yaml", "whitespace.yaml"],
            ],
            [/.*/, { token: "@rematch", nextEmbedded: "yaml", next: "@yamlRest" }],
        ],
        shellCommand: [
            [
                /\$\(/,
                {
                    token: "@rematch",
                    bracket: "@open",
                    next: "jsEmbedded",
                    log: "Open fragment",
                },
            ],
            [
                /./,
                {
                    cases: {
                        "@eos": {
                            token: "source.js",
                            next: "@pop",
                            log: "@eos",
                        },
                        default: {
                            token: "source.js",
                            log: "default",
                        },
                    },
                },
            ],
        ],
        jsEmbedded: [
            /* known problems:
              - end sequence `//end)` is awkward, if not used we only pop out of syntax highlighting at the end of a line
              - we always pop out of the embedded js highlighting on the end of the line
              - if we don't pop out at the of the line we might mark the whole document in js syntax
              - if we pop out of the embedded state on `)` the first function call (or other use of `)`) will end the js highlighting
            */
            [/\/\/end(?=\))/, { token: "comment", next: "@pop", nextEmbedded: "@pop", log: "pop embedded inline" }],
            [/$/, { token: "@rematch", next: "@pop", nextEmbedded: "@pop", log: "pop" }],
            [/[^(]+/, { token: "source.js", nextEmbedded: "javascript", log: "embedded source.js" }],
        ],
        requirements: [
            // Match array item in `requirements`
            [
                /(\s*)(-)(\s*)(type)(:)(\s*)(javascript)/,
                [
                    "whitespace",
                    "operators",
                    "whitespace",
                    "type",
                    "operators",
                    "whitespace",
                    { token: "string.yaml", next: "@javascriptRequirement", log: "array of" },
                ],
            ],
            [/.*/, { token: "@rematch", next: "@root" }], // Back to root if no match
        ],

        javascriptRequirement: [
            // Match `expression_lib` key followed by a block scalar array item
            [/\s*(expression_lib):\s*/, { token: "type.yaml", next: "@expressionLib", log: "expressionLib" }],
            [/.*/, { token: "@rematch", next: "@root" }], // Back to root if no match
        ],

        expressionLib: [
            // Match array item with block scalar `- |`
            [
                /\s*-\s*\|/,
                { token: "key", nextEmbedded: "javascript", next: "@jsBlockMultiline", log: "jsBlockMultiLine" },
            ],
            [/.*/, { token: "@rematch", next: "@root" }], // Back to root if no match
        ],
        // Inline JavaScript ends at the end of the line
        inlineJs: [
            [
                /$/,
                {
                    token: "@rematch",
                    nextEmbedded: "@pop",
                    next: "@pop",
                },
            ],
        ],
        jsBlockMultiline: [
            [
                /^\s*\w+:|^\s*$/,
                {
                    token: "@rematch",
                    nextEmbedded: "@pop",
                    next: "@pop",
                },
            ], // Key or blank line (end condition)
        ],
        // Delegate to YAML tokenizer for the rest
        yamlRest: [
            // Include YAML language tokenizer here
            [/$/, { token: "@rematch", nextEmbedded: "@pop", next: "@pop" }],
        ],
    },
};
