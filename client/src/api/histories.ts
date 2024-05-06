import { fetcher } from "@/api/schema";

export const historiesFetcher = fetcher.path("/api/histories").method("get").create();
export const archivedHistoriesFetcher = fetcher.path("/api/histories/archived").method("get").create();
export const deleteHistory = fetcher.path("/api/histories/{history_id}").method("delete").create();
export const deleteHistories = fetcher.path("/api/histories/batch/delete").method("put").create();
export const undeleteHistory = fetcher.path("/api/histories/deleted/{history_id}/undelete").method("post").create();
export const undeleteHistories = fetcher.path("/api/histories/batch/undelete").method("put").create();
export const publishedHistoriesFetcher = fetcher.path("/api/histories/published").method("get").create();
export const historyFetcher = fetcher.path("/api/histories/{history_id}").method("get").create();
export const updateHistoryItemsInBulk = fetcher
    .path("/api/histories/{history_id}/contents/bulk")
    .method("put")
    .create();
export const sharing = fetcher.path("/api/histories/{history_id}/sharing").method("get").create();
export const enableLink = fetcher.path("/api/histories/{history_id}/enable_link_access").method("put").create();
