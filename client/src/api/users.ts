import { fetcher } from "@/api/schema";

export const recalculateDiskUsage = fetcher.path("/api/users/current/recalculate_disk_usage").method("put").create();
export const fetchQuotaUsages = fetcher.path("/api/users/{user_id}/usage").method("get").create();
