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
