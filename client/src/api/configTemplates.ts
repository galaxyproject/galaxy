import { type components } from "@/api/schema";

export type CreateInstancePayload = components["schemas"]["CreateInstancePayload"];

export type Instance =
    | components["schemas"]["UserFileSourceModel"]
    | components["schemas"]["UserConcreteObjectStoreModel"];

export type TemplateVariable =
    | components["schemas"]["TemplateVariableString"]
    | components["schemas"]["TemplateVariableInteger"]
    | components["schemas"]["TemplateVariablePathComponent"]
    | components["schemas"]["TemplateVariableBoolean"];
export type TemplateSecret = components["schemas"]["TemplateSecret"];
export type VariableData = CreateInstancePayload["variables"];
export type VariableValueType = VariableData[keyof VariableData];
export type SecretData = CreateInstancePayload["secrets"];

export type PluginAspectStatus = components["schemas"]["PluginAspectStatus"];
export type PluginStatus = components["schemas"]["PluginStatus"];

export type UpgradeInstancePayload = components["schemas"]["UpgradeInstancePayload"];
export type TestUpgradeInstancePayload = components["schemas"]["TestUpgradeInstancePayload"];
export type UpdateInstancePayload = components["schemas"]["UpdateInstancePayload"];
export type TestUpdateInstancePayload = components["schemas"]["TestUpdateInstancePayload"];

export interface TemplateSummary {
    description: string | null;
    hidden?: boolean;
    id: string;
    name: string | null;
    secrets?: TemplateSecret[] | null;
    variables?: TemplateVariable[] | null;
    version?: number;
}
