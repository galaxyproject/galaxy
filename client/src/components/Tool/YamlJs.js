import * as monaco from "monaco-editor";
import TOOL_SOURCE_SCHEMA from "./ToolSourceSchema.json";
import { configureMonacoYaml } from "monaco-yaml";
import { useMonaco } from "@guolao/vue-monaco-editor";


const embeddedModelUri = monaco.Uri.parse("file://embedded-model.js");

export function setupMonaco(monaco) {
    // Define the custom YAML language with embedded JavaScript
    monaco.languages.register({ id: "yaml-with-js" });
    monaco.languages.register({ id: "typescript" });
    monaco.languages.register({ id: "javascript" });
    monaco.languages.register({ id: "yaml" });

    monaco.languages.setMonarchTokensProvider("yaml-with-js", {
        tokenizer: {
            root: [
                // Multiline JavaScript block
                [
                    /(script|code|javascript):\s*\|/,
                    { token: "key", nextEmbedded: "javascript", next: "@jsBlockMultiline" },
                ],
                // Inline JavaScript: Key followed by code on the same line
                [/(script|code|javascript):\s*/, { token: "key", nextEmbedded: "javascript", next: "@inlineJs" }],
                [/.*/, { token: "@rematch", nextEmbedded: "yaml", next: "@yamlRest" }],
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
    });
    monaco.languages.setLanguageConfiguration("yaml-with-js", {
        comments: { lineComment: "#" },
        brackets: [
            ["{", "}"],
            ["[", "]"],
            ["(", ")"],
        ],
        autoClosingPairs: [
            { open: "{", close: "}" },
            { open: "[", close: "]" },
            { open: "(", close: ")" },
            { open: '"', close: '"' },
            { open: "'", close: "'" },
        ],
        surroundingPairs: [
            { open: "{", close: "}" },
            { open: "[", close: "]" },
            { open: "(", close: ")" },
            { open: '"', close: '"' },
            { open: "'", close: "'" },
        ],
    });

    // Set TypeScript/JavaScript configuration
    monaco.languages.typescript.javascriptDefaults.setCompilerOptions({
        target: monaco.languages.typescript.ScriptTarget.ES2017,
        allowNonTsExtensions: true,
        strict: true,
        moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
        checkJs: true,
        noEmit: true,
    });

    const { dispose } = configureMonacoYaml(monaco, {
        enableSchemaRequest: false,
        schemas: [
            {
                // If YAML file is opened matching this glob
                fileMatch: ["tool.yml"],
                // The following schema will be applied
                schema: TOOL_SOURCE_SCHEMA,
                // And the URI will be linked to as the source.
                uri: "https://schema.galaxyproject.org/customTool.json",
            },
        ],
    });
    return dispose;
}

export async function setupEditor(editor) {
    console.log(editor.getModel("tool.yml"));
    // Virtual model for JavaScript
    const yamlModel = editor.getModels().find((item) => item.getLanguageId() == "yaml-with-js");
    const embeddedModel = editor.getModel(embeddedModelUri) || editor.createModel("", "typescript", embeddedModelUri);
    setupContentSync(yamlModel, embeddedModel);
    monaco.languages.registerHoverProvider("yaml-with-js", { provideHover });
    monaco.languages.registerCompletionItemProvider("yaml-with-js", { provideCompletionItems });
    attachDiagnosticsProvider(yamlModel, embeddedModel);
}

function extractEmbeddedJavaScript(yamlContent) {
    const scriptRegex = /(script|code|javascript):\s*(?:\|([\s\S]*?)(?=\n\s*\w+:|\n\s*$)|(.+))/g;
    const match = scriptRegex.exec(yamlContent);
    if (match) {
        if (match[2]) {
            return match[2];
        } else if (match[3]) {
            return match[3];
        }
    }
    return "";
}

export function setupContentSync(yamlModel, embeddedModel) {
    // Keep the embedded JavaScript model in sync with the YAML editor
    yamlModel.onDidChangeContent(() => {
        const yamlContent = yamlModel.getValue();
        const scriptContent = extractEmbeddedJavaScript(yamlContent);
        embeddedModel.setValue(scriptContent);
    });
}

// Add IntelliSense for the embedded JavaScript

export async function provideCompletionItems(model, position) {
    const yamlContent = model.getValue();
    const embeddedContent = extractEmbeddedJavaScript(yamlContent);

    if (embeddedContent) {
        const embeddedModel = monaco.editor.getModel(embeddedModelUri);
        const embeddedPosition = translateYamlPositionToEmbedded(model, position, embeddedModel, yamlContent);
        if (!embeddedPosition) return null;
        const worker = await monaco.languages.typescript.getTypeScriptWorker();
        const languageService = await worker(embeddedModelUri);

        const completionInfo = await languageService.getCompletionsAtPosition(
            embeddedModelUri.toString(),
            embeddedModel.getOffsetAt(embeddedPosition),
            {}
        );

        if (completionInfo && completionInfo.entries) {
            const wordInfo = model.getWordUntilPosition(position);

            return {
                suggestions: completionInfo.entries.map((entry) => ({
                    label: entry.name,
                    kind: monaco.languages.CompletionItemKind[entry.kind],
                    insertText: entry.name,
                    range: {
                        startLineNumber: position.lineNumber,
                        startColumn: wordInfo.startColumn,
                        endLineNumber: position.lineNumber,
                        endColumn: wordInfo.endColumn,
                    },
                })),
            };
        }
    }

    return { suggestions: [] };
}

function attachDiagnosticsProvider(yamlModel, embeddedModel) {
    monaco.editor.setModelMarkers(yamlModel, "owner", []); // Clear existing markers.

    yamlModel.onDidChangeContent(async () => {
        const yamlContent = yamlModel.getValue();
        const embeddedJavaScript = extractEmbeddedJavaScript(yamlContent);

        if (embeddedJavaScript) {
            const worker = await monaco.languages.typescript.getTypeScriptWorker();
            const languageService = await worker(embeddedModelUri);

            const diagnostics = await languageService.getSemanticDiagnostics(embeddedModelUri.toString());

            const markers = diagnostics.map((diagnostic) => {
                const startPosition = translateEmbeddedPositionToYaml(
                    embeddedModel,
                    diagnostic.start,
                    yamlModel,
                    yamlContent
                );
                const endPosition = translateEmbeddedPositionToYaml(
                    embeddedModel,
                    diagnostic.start + diagnostic.length,
                    yamlModel,
                    yamlContent
                );

                return {
                    severity: monaco.MarkerSeverity.Error, // Severity: Error, Warning, or Info
                    message: diagnostic.messageText,
                    startLineNumber: startPosition.lineNumber,
                    startColumn: startPosition.column,
                    endLineNumber: endPosition.lineNumber,
                    endColumn: endPosition.column,
                };
            });

            monaco.editor.setModelMarkers(yamlModel, "owner", markers);
        }
    });
}

export async function provideHover(model, position) {
    const yamlContent = model.getValue();
    const embeddedModel = monaco.editor.getModel(embeddedModelUri);
    const embeddedContent = extractEmbeddedJavaScript(yamlContent);

    if (embeddedContent) {
        const embeddedPosition = translateYamlPositionToEmbedded(model, position, embeddedModel, yamlContent);

        if (!embeddedPosition) return null;

        const worker = await monaco.languages.typescript.getTypeScriptWorker(); // Get JS worker
        const languageService = await worker(embeddedModelUri);

        const quickInfo = await languageService.getQuickInfoAtPosition(
            embeddedModelUri.toString(),
            embeddedModel.getOffsetAt(embeddedPosition)
        );

        if (quickInfo) {
            return {
                range: {
                    startLineNumber: position.lineNumber,
                    startColumn: position.column,
                    endLineNumber: position.lineNumber,
                    endColumn: position.column,
                },
                contents: [
                    { value: quickInfo.displayParts.map((p) => p.text).join("") },
                    { value: quickInfo.documentation },
                ],
            };
        }
    }
    return null;
}

function translateEmbeddedPositionToYaml(embeddedModel, embeddedOffset, yamlModel, yamlContent) {
    const scriptRegex = /(script|code|javascript):\s*(?:\|([\s\S]*?)(?=\n\s*\w+:|\n\s*$)|(.+))/; // No g flag
    const scriptMatch = yamlContent.match(scriptRegex);

    if (!scriptMatch) return null;

    let scriptStartIndex;
    if (scriptMatch[2]) {
        // Multiline
        scriptStartIndex = scriptMatch.index + scriptMatch[0].indexOf("|") + 1;
    } else if (scriptMatch[3]) {
        // Inline
        scriptStartIndex = scriptMatch.index + scriptMatch[0].indexOf(scriptMatch[3]); // Start of the inline code
    } else {
        return null; // Should not happen, but good to have
    }

    const yamlOffset = scriptStartIndex + embeddedOffset;
    return yamlModel.getPositionAt(yamlOffset);
}

function translateYamlPositionToEmbedded(yamlModel, yamlPosition, embeddedModel, yamlContent) {
    const scriptRegex = /(script|code|javascript):\s*(?:\|([\s\S]*?)(?=\n\s*\w+:|\n\s*$)|(.+))/; // No g flag
    const scriptMatch = yamlContent.match(scriptRegex);

    if (!scriptMatch) return null;

    let scriptStartIndex;
    let scriptEndIndex;
    if (scriptMatch[2]) {
        // Multiline
        scriptStartIndex = scriptMatch.index + scriptMatch[0].indexOf("|") + 1;
        scriptEndIndex = scriptMatch.index + scriptMatch[0].length; // End of the matched block
    } else if (scriptMatch[3]) {
        // Inline
        scriptStartIndex = scriptMatch.index + scriptMatch[0].indexOf(scriptMatch[3]);
        scriptEndIndex = scriptStartIndex + scriptMatch[3].length;
    } else {
        return null;
    }

    const yamlOffset = yamlModel.getOffsetAt(yamlPosition);

    if (yamlOffset >= scriptStartIndex && yamlOffset <= scriptEndIndex) {
        const embeddedOffset = yamlOffset - scriptStartIndex;
        return embeddedModel.getPositionAt(embeddedOffset);
    }
    return null;
}
