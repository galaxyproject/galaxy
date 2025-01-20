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
            [/(shell_command):\s*\|/, { token: "key", next: "@shellCommand" }],
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
            [/\/\/end\)/, { token: "comment", next: "@pop", nextEmbedded: "@pop", log: "pop" }],
            [/$/, { token: "@rematch", next: "@pop", nextEmbedded: "@pop", log: "pop" }],
            [/[^(]+/, { token: "source.js", nextEmbedded: "javascript", log: "embedded source.js" }],
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
