import { fetcher } from "@/api/schema";

export const deleteQuota = fetcher.path("/api/quotas/{id}").method("delete").create();
export const undeleteQuota = fetcher.path("/api/quotas/deleted/{id}/undelete").method("post").create();
