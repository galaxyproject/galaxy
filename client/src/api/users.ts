import { fetcher } from "@/api/schema";

export const createApiKey = fetcher.path("/api/users/{user_id}/api_key").method("post").create();
export const deleteUser = fetcher.path("/api/users/{user_id}").method("delete").create();
export const fetchQuotaUsages = fetcher.path("/api/users/{user_id}/usage").method("get").create();
export const recalculateDiskUsage = fetcher.path("/api/users/current/recalculate_disk_usage").method("put").create();
export const recalculateDiskUsageByUserId = fetcher
    .path("/api/users/{user_id}/recalculate_disk_usage")
    .method("put")
    .create();
export const sendActivationEmail = fetcher.path("/api/users/{user_id}/send_activation_email").method("post").create();
export const undeleteUser = fetcher.path("/api/users/deleted/{user_id}/undelete").method("post").create();

const getUsers = fetcher.path("/api/users").method("get").create();
export async function getAllUsers() {
    const { data } = await getUsers({});
    return data;
}
