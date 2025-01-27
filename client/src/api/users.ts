import { type components, GalaxyApi } from "@/api";
import { toQuotaUsage } from "@/components/User/DiskUsage/Quota/model";
import { rethrowSimple } from "@/utils/simple-error";

export { type QuotaUsage } from "@/components/User/DiskUsage/Quota/model";

export async function fetchCurrentUserQuotaUsages() {
    const { data, error } = await GalaxyApi().GET("/api/users/{user_id}/usage", {
        params: { path: { user_id: "current" } },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data.map((usage) => toQuotaUsage(usage));
}

export async function fetchCurrentUserQuotaSourceUsage(quotaSourceLabel?: string | null) {
    if (!quotaSourceLabel) {
        quotaSourceLabel = "__null__";
    }

    const { data, error } = await GalaxyApi().GET("/api/users/{user_id}/usage/{label}", {
        params: { path: { user_id: "current", label: quotaSourceLabel } },
    });

    if (error) {
        rethrowSimple(error);
    }

    if (data === null) {
        return null;
    }

    return toQuotaUsage(data);
}

export type CreateSourceCredentialsPayload = components["schemas"]["CreateSourceCredentialsPayload"];
export type ServiceCredentialPayload = components["schemas"]["ServiceCredentialPayload"];
export type ServiceGroupPayload = components["schemas"]["ServiceGroupPayload"];
export type UserCredentials = components["schemas"]["UserCredentialsResponse"];

// TODO: Change API to directly return the correct type to avoid this transformation and additional type definitions.
export function transformToSourceCredentials(
    toolId: string,
    toolCredentialsDefinition: ServiceCredentialsDefinition[]
): SourceCredentialsDefinition {
    return {
        sourceType: "tool",
        sourceId: toolId,
        services: new Map(toolCredentialsDefinition.map((service) => [service.service_reference, service])),
    };
}

/**
 * Represents the definition of credentials for a particular service.
 */
export interface ServiceCredentialsDefinition {
    service_reference: string;
    name: string;
    optional: boolean;
    multiple: boolean;
    label?: string;
    description?: string;
    variables: ServiceVariableDefinition[];
    secrets: ServiceVariableDefinition[];
}

/**
 * Represents the definition of credentials for a particular source.
 * A source can be a tool, a workflow, etc.Base interface for credentials definitions.
 * A source may accept multiple services, each with its own credentials.
 */
export interface SourceCredentialsDefinition {
    sourceType: string;
    sourceId: string;
    services: Map<string, ServiceCredentialsDefinition>;
}

/**
 * Base interface for credential details. It is used to define the structure of variables and secrets.
 */
export interface ServiceVariableDefinition {
    name: string;
    label?: string;
    description?: string;
}
