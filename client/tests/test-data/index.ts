import type { HistorySummary, RegisteredUser } from "@/api";
import type { UserQuotaUsageData } from "@/components/User/DiskUsage/Quota/model/QuotaUsage";

export function getFakeRegisteredUser(data: Partial<RegisteredUser> = {}): RegisteredUser {
    return {
        id: "fake_user_id",
        email: "fake_user_email",
        isAnonymous: false,
        username: "fake_username",
        total_disk_usage: 0,
        nice_total_disk_usage: "0.0 bytes",
        deleted: false,
        purged: false,
        is_admin: false,
        preferences: {},
        quota: "default",
        ...data,
    };
}

export function getFakeHistorySummary(data: Partial<HistorySummary> = {}): HistorySummary {
    return {
        id: "fake_history_id",
        name: "Unnamed history",
        model_class: "History",
        annotation: null,
        archived: false,
        count: 0,
        deleted: false,
        purged: false,
        published: false,
        tags: [],
        update_time: "2026-01-01T00:00:00",
        url: "/api/histories/fake_history_id",
        ...data,
    };
}

/** The usage of a storage source as the server reports it, by default with a quota of 1000 bytes. */
export function getFakeQuotaUsageData(label: string | null, usage: number, quota = 1000): UserQuotaUsageData {
    return {
        quota_source_label: label,
        total_disk_usage: usage,
        quota_bytes: quota,
        // The server caps the percentage at 100
        quota_percent: Math.min(100, Math.round((usage / quota) * 100)),
    };
}
