import { fetcher } from "@/api/schema";

export const postFolderContent = fetcher.path("/api/folders/{folder_id}/contents").method("post").create();
