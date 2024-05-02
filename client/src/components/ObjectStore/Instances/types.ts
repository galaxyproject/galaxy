import type { components } from "@/api/schema/schema";

export type UserConcreteObjectStore = components["schemas"]["UserConcreteObjectStoreModel"];
export type CreateInstancePayload = components["schemas"]["CreateInstancePayload"];
export type ObjectStoreTemplateVariable = components["schemas"]["ObjectStoreTemplateVariable"];
export type ObjectStoreTemplateSecret = components["schemas"]["ObjectStoreTemplateSecret"];
export type VariableValueType = (string | boolean | number) | undefined;
export type VariableData = { [key: string]: VariableValueType };
export type SecretData = { [key: string]: string };
