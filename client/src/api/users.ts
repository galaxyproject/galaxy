import { GalaxyApi } from "@/api";
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

// TODO: Temporarily using these interfaces until the new API is implemented
export interface CredentialsDefinition {
    name: string;
    reference: string;
    optional: boolean;
    multiple: boolean;
    label?: string;
    description?: string;
}
export interface UserCredentials extends CredentialsDefinition {
    variables: Variable[];
    secrets: Secret[];
}

export interface ToolCredentialsDefinition extends CredentialsDefinition {
    variables: CredentialDetail[];
    secrets: CredentialDetail[];
}

export interface CredentialDetail {
    name: string;
    label?: string;
    description?: string;
}

export interface Secret extends CredentialDetail {
    alreadySet: boolean;
    value?: string;
}

export interface Variable extends CredentialDetail {
    value?: string;
}
