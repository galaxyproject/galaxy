import {
    fromCodeActionContext,
    fromFormattingOptions,
    fromPosition,
    fromRange,
    toCodeAction,
    toCompletionList,
    toDocumentSymbol,
    toFoldingRange,
    toHover,
    toLink,
    toLocationLink,
    toMarkerData,
    toSelectionRanges,
    toTextEdit,
} from "monaco-languageserver-types";
import type { IDisposable, IPosition, MonacoEditor } from "monaco-types";
import { createWorkerManager } from "monaco-worker-manager";
import type { CompletionItemKind, FormattingOptions } from "vscode-languageserver-types";

export interface JSONSchema {
    id?: string;
    $id?: string;
    $schema?: string;
    url?: string;
    type?: string[] | string;
    title?: string;
    closestTitle?: string;
    versions?: Record<string, string>;
    default?: unknown;
    definitions?: Record<string, JSONSchema>;
    description?: string;
    properties?: Record<string, JSONSchema | boolean>;
    patternProperties?: Record<string, JSONSchema | boolean>;
    additionalProperties?: JSONSchema | boolean;
    minProperties?: number;
    maxProperties?: number;
    dependencies?: Record<string, JSONSchema | string[] | boolean>;
    items?: (JSONSchema | boolean)[] | JSONSchema | boolean;
    minItems?: number;
    maxItems?: number;
    uniqueItems?: boolean;
    additionalItems?: JSONSchema | boolean;
    pattern?: string;
    minLength?: number;
    maxLength?: number;
    minimum?: number;
    maximum?: number;
    exclusiveMinimum?: boolean | number;
    exclusiveMaximum?: boolean | number;
    multipleOf?: number;
    required?: string[];
    $ref?: string;
    anyOf?: (JSONSchema | boolean)[];
    allOf?: (JSONSchema | boolean)[];
    oneOf?: (JSONSchema | boolean)[];
    not?: JSONSchema | boolean;
    enum?: unknown[];
    format?: string;
    const?: unknown;
    contains?: JSONSchema | boolean;
    propertyNames?: JSONSchema | boolean;
    examples?: unknown[];
    $comment?: string;
    if?: JSONSchema | boolean;
    then?: JSONSchema | boolean;
    else?: JSONSchema | boolean;
    defaultSnippets?: {
        label?: string;
        description?: string;
        markdownDescription?: string;
        type?: string;
        suggestionKind?: CompletionItemKind;
        sortText?: string;
        body?: unknown;
        bodyText?: string;
    }[];
    errorMessage?: string;
    patternErrorMessage?: string;
    deprecationMessage?: string;
    enumDescriptions?: string[];
    markdownEnumDescriptions?: string[];
    markdownDescription?: string;
    doNotSuggest?: boolean;
    allowComments?: boolean;
    schemaSequence?: JSONSchema[];
    filePatternAssociation?: string;
}

export interface SchemasSettings {
    /**
     * A `Uri` file match which will trigger the schema validation. This may be a glob or an exact
     * path.
     *
     * @example '.gitlab-ci.yml'
     * @example 'file://**\/.github/actions/*.yaml'
     */
    fileMatch: string[];

    /**
     * The JSON schema which will be used for validation. If not specified, it will be downloaded from
     * `uri`.
     */
    schema?: JSONSchema;

    /**
     * The source URI of the JSON schema. The JSON schema will be downloaded from here if no schema
     * was supplied. It will also be displayed as the source in hover tooltips.
     */
    uri: string;
}

export interface MonacoYamlOptions {
    /**
     * If set, enable schema based autocompletion.
     *
     * @default true
     */
    readonly completion?: boolean;

    /**
     * A list of custom tags.
     *
     * @default []
     */
    readonly customTags?: string[];

    /**
     * If set, the schema service will load schema content on-demand.
     *
     * @default false
     */
    readonly enableSchemaRequest?: boolean;

    /**
     * If true, formatting using Prettier is enabled. Setting this to `false` does **not** exclude
     * Prettier from the bundle.
     *
     * @default true
     */
    readonly format?: boolean;

    /**
     * If set, enable hover typs based the JSON schema.
     *
     * @default true
     */
    readonly hover?: boolean;

    /**
     * If true, a different diffing algorithm is used to generate error messages.
     *
     * @default false
     */
    readonly isKubernetes?: boolean;

    /**
     * A list of known schemas and/or associations of schemas to file names.
     *
     * @default []
     */
    readonly schemas?: SchemasSettings[];

    /**
     * If set, the validator will be enabled and perform syntax validation as well as schema
     * based validation.
     *
     * @default true
     */
    readonly validate?: boolean;

    /**
     * The YAML version to use for parsing.
     *
     * @default '1.2'
     */
    readonly yamlVersion?: "1.1" | "1.2";
}

export interface MonacoYaml extends IDisposable {
    /**
     * Recondigure `monaco-yaml`.
     */
    update: (options: MonacoYamlOptions) => Promise<undefined>;
}

export function buildProviderFunctions(monaco: MonacoEditor, options?: MonacoYamlOptions) {
    const createData: MonacoYamlOptions = {
        completion: true,
        customTags: [],
        enableSchemaRequest: false,
        format: true,
        isKubernetes: false,
        hover: true,
        schemas: [],
        validate: true,
        yamlVersion: "1.2",
        ...options,
    };

    const workerManager = createWorkerManager(monaco, {
        label: "yaml",
        moduleId: "monaco-yaml/yaml.worker",
        createData,
    });

    const providerFunctions = {
        autoFormatTriggerCharacters: ["\n"],
        triggerCharacters: [" ", ":"],
        displayName: "yaml",

        async provideMarkerData(model: any) {
            const worker = await workerManager.getWorker(model.uri);
            const diagnostics = await (worker as any).doValidation(String(model.uri));

            return diagnostics?.map(toMarkerData);
        },

        async resetMarkerData(model: any) {
            const worker = await workerManager.getWorker(model.uri);
            await (worker as any).resetSchema(String(model.uri));
        },

        async provideCompletionItems(model: any, position: IPosition) {
            const wordInfo = model.getWordUntilPosition(position);
            const worker = await workerManager.getWorker(model.uri);
            const info = await (worker as any).doComplete(String(model.uri), fromPosition(position));

            if (info) {
                return toCompletionList(info, {
                    range: {
                        startLineNumber: position.lineNumber,
                        startColumn: wordInfo.startColumn,
                        endLineNumber: position.lineNumber,
                        endColumn: wordInfo.endColumn,
                    },
                });
            }
        },

        async provideHover(model: any, position: IPosition) {
            const worker = await workerManager.getWorker(model.uri);
            const info = await (worker as any).doHover(String(model.uri), fromPosition(position));

            if (info) {
                return toHover(info);
            }
        },

        async provideDefinition(model: any, position: IPosition) {
            const worker = await workerManager.getWorker(model.uri);
            const locationLinks = await (worker as any).doDefinition(String(model.uri), fromPosition(position));

            return locationLinks?.map(toLocationLink);
        },

        async provideDocumentSymbols(model: any) {
            const worker = await workerManager.getWorker(model.uri);
            const items = await (worker as any).findDocumentSymbols(String(model.uri));

            return items?.map(toDocumentSymbol);
        },

        async provideDocumentFormattingEdits(model: any) {
            const worker = await workerManager.getWorker(model.uri);
            const edits = await (worker as any).format(String(model.uri));

            return edits?.map(toTextEdit);
        },

        async provideLinks(model: any) {
            const worker = await workerManager.getWorker(model.uri);
            const links = await (worker as any).findLinks(String(model.uri));

            if (links) {
                return {
                    links: links.map(toLink),
                };
            }
        },

        async provideCodeActions(model: any, range: any, context: any) {
            const worker = await workerManager.getWorker(model.uri);
            const codeActions = await (worker as any).getCodeAction(
                String(model.uri),
                fromRange(range),
                fromCodeActionContext(context)
            );

            if (codeActions) {
                return {
                    actions: codeActions.map(toCodeAction),
                    dispose() {
                        // This is required by the TypeScript interface, but it’s not implemented.
                    },
                };
            }
        },

        async provideFoldingRanges(model: any) {
            const worker = await workerManager.getWorker(model.uri);
            const foldingRanges = await (worker as any).getFoldingRanges(String(model.uri));

            return foldingRanges?.map(toFoldingRange);
        },

        async provideOnTypeFormattingEdits(
            model: any,
            position: IPosition,
            ch: any,
            formattingOptions: FormattingOptions
        ) {
            const worker = await workerManager.getWorker(model.uri);
            const edits = await (worker as any).doDocumentOnTypeFormatting(
                String(model.uri),
                fromPosition(position),
                ch,
                fromFormattingOptions(formattingOptions)
            );

            return edits?.map(toTextEdit);
        },

        async provideSelectionRanges(model: any, positions: IPosition[]) {
            const worker = await workerManager.getWorker(model.uri);
            const selectionRanges = await (worker as any).getSelectionRanges(
                String(model.uri),
                positions.map(fromPosition)
            );

            return selectionRanges?.map(toSelectionRanges);
        },
    };
    return { dispose: workerManager, providerFunctions };
}
