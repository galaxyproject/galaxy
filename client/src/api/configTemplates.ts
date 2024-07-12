import type { components } from "@/api/schema/schema";

export type Instance =
    | components["schemas"]["UserFileSourceModel"]
    | components["schemas"]["UserConcreteObjectStoreModel"];

export type TemplateVariable =
    | components["schemas"]["TemplateVariableString"]
    | components["schemas"]["TemplateVariableInteger"]
    | components["schemas"]["TemplateVariablePathComponent"]
    | components["schemas"]["TemplateVariableBoolean"];
export type TemplateSecret = components["schemas"]["TemplateSecret"];
export type VariableValueType = string | boolean | number;
export type VariableData = { [key: string]: VariableValueType };
export type SecretData = { [key: string]: string };

export type PluginAspectStatus = components["schemas"]["PluginAspectStatus"];
export type PluginStatus = components["schemas"]["PluginStatus"];

export interface TemplateSummary {
    description: string | null;
    hidden?: boolean;
    id: string;
    name: string | null;
    secrets?: TemplateSecret[] | null;
    variables?: TemplateVariable[] | null;
    version?: number;
}
