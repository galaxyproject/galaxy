import type { HistorySummary, RegisteredUser } from "@/api";

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
