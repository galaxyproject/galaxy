import * as monaco from "monaco-editor";
import { editor } from "monaco-editor";
import { type IPosition, type MonacoEditor } from "monaco-types";
import { configureMonacoYaml } from "monaco-yaml";

import { extractEmbeddedJs } from "./extractEmbeddedJs";
import { monarchConfig } from "./MonarchYamlJs";
import { fetchAndConvertSchemaToInterface } from "./runTimeModel";
import TOOL_SOURCE_SCHEMA from "./ToolSourceSchema.json";
import { buildProviderFunctions } from "./yaml";

const LANG = "yaml-with-js";

const embeddedModelUri = monaco.Uri.parse("file://embedded-model.js");
const defModelUri = monaco.Uri.parse("file://runtime-defs.ts");

export async function setupMonaco(monaco: MonacoEditor) {
    // Define the custom YAML language with embedded JavaScript
    monaco.languages.register({ id: LANG });
    monaco.languages.register({ id: "typescript" });
    monaco.languages.register({ id: "javascript" });
    monaco.languages.register({ id: "yaml" });
    const disposables: monaco.IDisposable[] = [];

    disposables.push(monaco.languages.setMonarchTokensProvider(LANG, monarchConfig));
    disposables.push(
        monaco.languages.setLanguageConfiguration(LANG, {
            comments: { lineComment: "#" },
            brackets: [
                ["{", "}"],
                ["[", "]"],
                ["(", ")"],
                ["$(", ")"],
            ],
            autoClosingPairs: [
                { open: "{", close: "}" },
                { open: "[", close: "]" },
                { open: "(", close: ")" },
                { open: '"', close: '"' },
                { open: "'", close: "'" },
                { open: "$(", close: ")" },
            ],
            surroundingPairs: [
                { open: "{", close: "}" },
                { open: "[", close: "]" },
                { open: "(", close: ")" },
                { open: '"', close: '"' },
                { open: "'", close: "'" },
            ],
        })
    );

    // Set TypeScript/JavaScript configuration
    monaco.languages.typescript.typescriptDefaults.setCompilerOptions({
        target: monaco.languages.typescript.ScriptTarget.ES2017,
        allowNonTsExtensions: true,
        strict: true,
        moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
        checkJs: true,
        noEmit: true,
        lib: ["es2017"],
    });
    monaco.languages.typescript.typescriptDefaults.setEagerModelSync(true);
    addExtraLibs();

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
    const { dispose: disposeWorker, providerFunctions } = buildProviderFunctions(monaco, {
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
    disposables.push(disposeWorker);
    const moreDisposeables = await setupEditor(providerFunctions);
    function disposeEditor() {
        dispose();
        monaco.editor.getModels().map((model) => model.dispose());
        [...disposables, ...moreDisposeables].map((disposable) => disposable.dispose());
    }
    return disposeEditor;
}

export async function setupEditor(providerFunctions: any) {
    const disposables = [];
    // Virtual model for JavaScript
    const yamlModel = editor.getModels().find((item) => item.getLanguageId() == LANG)!;
    const embeddedModel = editor.getModel(embeddedModelUri) || editor.createModel("", "typescript", embeddedModelUri);
    mixJsYamlProviders(providerFunctions);
    disposables.push(monaco.languages.registerHoverProvider(LANG, providerFunctions));
    disposables.push(
        monaco.languages.registerCompletionItemProvider(LANG, {
            triggerCharacters: ["."],
            provideCompletionItems: providerFunctions.provideCompletionItems,
        })
    );
    disposables.push(monaco.languages.registerDefinitionProvider(LANG, providerFunctions));
    disposables.push(monaco.languages.registerDocumentSymbolProvider(LANG, providerFunctions));
    disposables.push(monaco.languages.registerDocumentFormattingEditProvider(LANG, providerFunctions));
    disposables.push(monaco.languages.registerLinkProvider(LANG, providerFunctions));
    disposables.push(monaco.languages.registerCodeActionProvider(LANG, providerFunctions));
    disposables.push(monaco.languages.registerFoldingRangeProvider(LANG, providerFunctions));
    disposables.push(monaco.languages.registerOnTypeFormattingEditProvider(LANG, providerFunctions));
    disposables.push(monaco.languages.registerSelectionRangeProvider(LANG, providerFunctions));

    attachDiagnosticsProvider(yamlModel, embeddedModel, providerFunctions.provideMarkerData);
    return disposables;
}

function extractExpressionLibJavaScript(yamlContent: string) {
    const scriptRegex = /(expression_lib):\s*-\s*\|([\s\S]*?)(?=\n\s*-\s|\n\s*\w+:|\n\s*$)/g;
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

const fragment = `
declare global {
    const inputs: components["schemas"]["inputs"]
}
`;

async function addExtraLibs(yamlContent?: string) {
    if (yamlContent) {
        const { schemaInterface, error } = await fetchAndConvertSchemaToInterface(yamlContent);
        if (error) {
            console.error(error);
        } else {
            const runtimeFragment = `${schemaInterface}\n${fragment}`;
            const runtimeModel = editor.getModel(defModelUri) || editor.createModel("", "typescript", defModelUri);
            if (runtimeModel.getValue() != runtimeFragment) {
                runtimeModel.setValue(runtimeFragment);
            }
        }
    }
}

export async function contentSync(yamlContent: string, scriptContent: string, embeddedModel: editor.ITextModel) {
    // Keep the embedded JavaScript model in sync with the YAML editor
    if (yamlContent) {
        await addExtraLibs(yamlContent);
    }
    embeddedModel.setValue(scriptContent);
}

async function mixJsYamlProviders(yamlProviderFunctions: any) {
    // Complete and hover consume position and return null if not in focus,
    // so execute JS provider, then yaml as fallback
    const yamlProvideCompletionItems = yamlProviderFunctions.provideCompletionItems;
    const yamlProvideHover = yamlProviderFunctions.provideHover;
    yamlProviderFunctions.provideCompletionItems = async (model: editor.ITextModel, position: IPosition) => {
        const jsCompletions = await provideCompletionItems(model, position);
        if (jsCompletions?.suggestions?.length > 0) {
            return jsCompletions;
        } else {
            return await yamlProvideCompletionItems(model, position);
        }
    };
    yamlProviderFunctions.provideHover = async (model: editor.ITextModel, position: IPosition) =>
        (await provideHover(model, position)) || (await yamlProvideHover(model, position));
}

async function languageServiceForModel(model: editor.ITextModel) {
    const worker = await monaco.languages.typescript.getTypeScriptWorker();
    const languageService = await worker(model.uri);
    return languageService;
}

async function allModels(model: editor.ITextModel) {
    const yamlContent = model.getValue();
    const embeddedModel = monaco.editor.getModel(embeddedModelUri)!;
    const embeddedStart = yamlContent.indexOf(embeddedModel.getValue());
    const models = [{ start: embeddedStart, model: embeddedModel }];
    const embeddedContents = extractEmbeddedJs(yamlContent);
    const fragmentModels = embeddedContents.map((fragment, index) => {
        const fragmentModel = getOrCreateFragmentModel(index, fragment.fragment);
        return {
            start: fragment.start,
            model: fragmentModel,
        };
    });
    return [...models, ...fragmentModels];
}

function getOrCreateFragmentModel(index: number, value: string) {
    const modelUri = monaco.Uri.parse(`file://temp-fragment-${index}`);
    const fragmentModel = monaco.editor.getModel(modelUri) || monaco.editor.createModel(value, "typescript", modelUri);
    fragmentModel.setValue(value);
    return fragmentModel;
}

async function modelForCurrentPosition(model: editor.ITextModel, position: IPosition) {
    const yamlContent = model.getValue();
    const embeddedContents = extractEmbeddedJs(yamlContent);
    const offsetForPosition = model.getOffsetAt(position);
    const fragmentIndex = embeddedContents.findIndex(
        (content) => content.start <= offsetForPosition && content.start + content.fragment.length >= offsetForPosition
    );
    if (fragmentIndex >= 0) {
        const fragment = embeddedContents[fragmentIndex]!;
        const offsetWithinFragment = offsetForPosition - fragment.start;
        const fragmentModel = getOrCreateFragmentModel(fragmentIndex, fragment.fragment);
        return { offset: offsetWithinFragment, model: fragmentModel };
    }
    const embeddedContent = extractExpressionLibJavaScript(yamlContent);
    if (embeddedContent) {
        const offsetWithinFragment = offsetForPosition - yamlContent.indexOf(embeddedContent);
        if (offsetWithinFragment < 0 || offsetWithinFragment > embeddedContent.length) {
            return undefined;
        }
        const embeddedModel = monaco.editor.getModel(embeddedModelUri)!;
        embeddedModel.setValue(embeddedContent);
        return { offset: offsetWithinFragment, model: embeddedModel };
    }
    return undefined;
}

// Add IntelliSense for the embedded JavaScript
async function provideCompletionItems(model: editor.ITextModel, position: IPosition) {
    let completionInfo: any;
    const currentData = await modelForCurrentPosition(model, position);
    if (currentData) {
        const { offset, model: currentModel } = currentData;
        const languageService = await languageServiceForModel(currentModel);
        completionInfo = await languageService.getCompletionsAtPosition(currentModel.uri.toString(), offset);

        if (completionInfo && completionInfo.entries) {
            const wordInfo = model.getWordUntilPosition(position);

            return {
                suggestions: completionInfo.entries.map((entry: any) => ({
                    label: entry.name,
                    kind: monaco.languages.CompletionItemKind[entry.kind[0].toUpperCase() + entry.kind.slice(1)],
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

function attachDiagnosticsProvider(
    yamlModel: editor.ITextModel,
    embeddedModel: editor.ITextModel,
    provideMarkerData: any
) {
    monaco.editor.setModelMarkers(yamlModel, "owner", []); // Clear existing markers.

    yamlModel.onDidChangeContent(async () => {
        const yamlContent = yamlModel.getValue();
        const embeddedJavaScript = extractExpressionLibJavaScript(yamlContent);
        // contentSync makes API call, we could consider updating the marker
        // only when fetch complete, but doesn't seem to be a problem ...
        await contentSync(yamlContent, embeddedJavaScript, embeddedModel);
        const yamlMarkers = await provideMarkerData(yamlModel);
        const models = await allModels(yamlModel);
        const worker = await monaco.languages.typescript.getTypeScriptWorker();
        const markers = [...yamlMarkers];
        const promises = models.map(async (modelData) => {
            const languageService = await worker(modelData.model.uri);
            const diagnostics = await languageService.getSemanticDiagnostics(modelData.model.uri.toString());
            diagnostics.forEach((diagnostic) => {
                const startPosition = yamlModel.getPositionAt(modelData.start + diagnostic.start!);
                const endPosition = yamlModel.getPositionAt(modelData.start + diagnostic.start! + diagnostic.length!);
                markers.push({
                    severity: monaco.MarkerSeverity.Error, // Severity: Error, Warning, or Info
                    message:
                        typeof diagnostic.messageText === "string"
                            ? diagnostic.messageText
                            : diagnostic.messageText.messageText,
                    startLineNumber: startPosition.lineNumber,
                    startColumn: startPosition.column,
                    endLineNumber: endPosition.lineNumber,
                    endColumn: endPosition.column,
                });
            });
        });
        await Promise.all(promises);
        monaco.editor.setModelMarkers(yamlModel, "owner", markers);
    });
}

function quickInfoToMarkdown(quickInfo: any, position: IPosition) {
    const { displayParts, documentation, tags } = quickInfo;
    const markdownText = [];

    // Format displayParts as code
    if (displayParts && displayParts.length > 0) {
        const signature = displayParts.map((part: any) => part.text).join("");
        markdownText.push({ value: "```ts\n" + signature + "\n```" });
    }

    // Add documentation text
    if (documentation && documentation.length > 0) {
        const docText = documentation.map((part: any) => part.text).join("");
        markdownText.push({ value: docText });
    }

    // Add tag text (e.g. @description)
    if (tags && tags.length > 0) {
        tags.forEach((tag: any) => {
            if (tag.text && Array.isArray(tag.text)) {
                const tagText = tag.text.map((t: any) => t.text).join("");
                markdownText.push({ value: `**@${tag.name}** — ${tagText}` });
            } else if (typeof tag.text === "string") {
                markdownText.push({ value: `**@${tag.name}** — ${tag.text}` });
            }
        });
    }
    return {
        range: {
            startLineNumber: position.lineNumber,
            startColumn: position.column,
            endLineNumber: position.lineNumber,
            endColumn: position.column,
        },
        contents: markdownText,
    };
}

async function provideHover(model: editor.ITextModel, position: IPosition) {
    const currentData = await modelForCurrentPosition(model, position);
    if (currentData) {
        const languageService = await languageServiceForModel(currentData.model);
        const quickInfo = await languageService.getQuickInfoAtPosition(
            currentData.model.uri.toString(),
            currentData.offset
        );
        if (quickInfo) {
            return quickInfoToMarkdown(quickInfo, position);
        }
    }
    return null;
}
