import * as monaco from "monaco-editor";
import { configureMonacoYaml } from "monaco-yaml";

import TOOL_SOURCE_SCHEMA from "./ToolSourceSchema.json";
import { buildProviderFunctions } from "./yaml";

const LANG = "yaml-with-js";

const embeddedModelUri = monaco.Uri.parse("file://embedded-model.js");

export function setupMonaco(monaco) {
    // Define the custom YAML language with embedded JavaScript
    monaco.languages.register({ id: LANG });
    monaco.languages.register({ id: "typescript" });
    monaco.languages.register({ id: "javascript" });
    monaco.languages.register({ id: "yaml" });

    monaco.languages.setMonarchTokensProvider(LANG, {
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
    monaco.languages.setLanguageConfiguration(LANG, {
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
    const providerFunctions = buildProviderFunctions(monaco, {
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
    return { dispose, providerFunctions };
}

export async function setupEditor(editor, providerFunctions) {
    // Virtual model for JavaScript
    const yamlModel = editor.getModels().find((item) => item.getLanguageId() == LANG);
    const embeddedModel = editor.getModel(embeddedModelUri) || editor.createModel("", "typescript", embeddedModelUri);
    setupContentSync(yamlModel, embeddedModel);
    mixJsYamlProviders(providerFunctions);
    monaco.languages.registerHoverProvider(LANG, providerFunctions);
    monaco.languages.registerCompletionItemProvider(LANG, providerFunctions);
    monaco.languages.registerDefinitionProvider(LANG, providerFunctions);
    monaco.languages.registerDocumentSymbolProvider(LANG, providerFunctions);
    monaco.languages.registerDocumentFormattingEditProvider(LANG, providerFunctions);
    monaco.languages.registerLinkProvider(LANG, providerFunctions);
    monaco.languages.registerCodeActionProvider(LANG, providerFunctions);
    monaco.languages.registerFoldingRangeProvider(LANG, providerFunctions);
    monaco.languages.registerOnTypeFormattingEditProvider(LANG, providerFunctions);
    monaco.languages.registerSelectionRangeProvider(LANG, providerFunctions);

    attachDiagnosticsProvider(yamlModel, embeddedModel, providerFunctions.provideMarkerData);
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

async function mixJsYamlProviders(yamlProviderFunctions) {
    // Complete and hover consume position and return null if not in focus,
    // so execute JS provider, then yaml as fallback
    const yamlProvideCompletionItems = yamlProviderFunctions.provideCompletionItems;
    const yamlProvideHover = yamlProviderFunctions.provideHover;
    yamlProviderFunctions.provideCompletionItems = async (model, position) => {
        const jsCompletions = await provideCompletionItems(model, position);
        if (jsCompletions?.suggestions?.length > 0) {
            return jsCompletions;
        } else {
            return await yamlProvideCompletionItems(model, position);
        }
    };
    yamlProviderFunctions.provideHover = async (model, position) =>
        (await provideHover(model, position)) || (await yamlProvideHover(model, position));
}

// Add IntelliSense for the embedded JavaScript
async function provideCompletionItems(model, position) {
    const yamlContent = model.getValue();
    const embeddedContent = extractEmbeddedJavaScript(yamlContent);

    if (embeddedContent) {
        const embeddedModel = monaco.editor.getModel(embeddedModelUri);
        const embeddedPosition = translateYamlPositionToEmbedded(model, position, embeddedModel, yamlContent);
        if (!embeddedPosition) {
            return null;
        }
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

function attachDiagnosticsProvider(yamlModel, embeddedModel, provideMarkerData) {
    monaco.editor.setModelMarkers(yamlModel, "owner", []); // Clear existing markers.

    yamlModel.onDidChangeContent(async () => {
        const yamlContent = yamlModel.getValue();
        const embeddedJavaScript = extractEmbeddedJavaScript(yamlContent);
        const yamlMarkers = await provideMarkerData(yamlModel);
        let jsMarkers = [];

        if (embeddedJavaScript) {
            const worker = await monaco.languages.typescript.getTypeScriptWorker();
            const languageService = await worker(embeddedModelUri);

            const diagnostics = await languageService.getSemanticDiagnostics(embeddedModelUri.toString());

            jsMarkers = diagnostics.map((diagnostic) => {
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
        }
        monaco.editor.setModelMarkers(yamlModel, "owner", [...yamlMarkers, ...jsMarkers]);
    });
}

async function provideHover(model, position) {
    const yamlContent = model.getValue();
    const embeddedModel = monaco.editor.getModel(embeddedModelUri);
    const embeddedContent = extractEmbeddedJavaScript(yamlContent);

    if (embeddedContent) {
        const embeddedPosition = translateYamlPositionToEmbedded(model, position, embeddedModel, yamlContent);

        if (!embeddedPosition) {
            return null;
        }

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

    if (!scriptMatch) {
        return null;
    }

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

    if (!scriptMatch) {
        return null;
    }

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
