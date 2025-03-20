import { type RegisteredUser } from "@/api";

export function getFakeRegisteredUser(data: Partial<RegisteredUser> = {}): RegisteredUser {
    return {
        id: "fake_user_id",
        email: "fake_user_email",
        tags_used: [],
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
