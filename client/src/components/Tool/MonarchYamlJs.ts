import { type languages } from "monaco-editor/esm/vs/editor/editor.api";

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
            // Multiline JavaScript block
            [/(expressionLib):\s*\|/, { token: "key", nextEmbedded: "javascript", next: "@jsBlockMultiline" }],
            // Inline JavaScript: Key followed by code on the same line
            [/(expressionLib):\s*/, { token: "key", nextEmbedded: "javascript", next: "@inlineJs" }],
            [/(shell_command):\s*/, { token: "key", next: "@shellCommand" }],
            [/.*/, { token: "@rematch", nextEmbedded: "yaml", next: "@yamlRest" }],
        ],
        shellCommand: [
            [
                /\$\(/,
                {
                    token: "@rematch",
                    bracket: "@open",
                    next: "jsEmbedded",
                },
            ],
            [
                /./,
                {
                    cases: {
                        "@eos": {
                            token: "source.js",
                            next: "@pop",
                        },
                        default: {
                            token: "source.js",
                        },
                    },
                },
            ],
        ],
        jsEmbedded: [
            // Hack? `)` would normally end the JS scope without some clever
            // regex that counts how many times we can use `)` before we quit the embedded javascript state.
            // The workaround is to open another jsEmbedded state when encountering `(`.
            [/\(/, { token: "parens", next: "jsEmbedded" }],
            [/\)/, { token: "@rematch", next: "@pop", nextEmbedded: "@pop" }],
            [/[^(]+/, { token: "source.js", nextEmbedded: "javascript" }],
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
