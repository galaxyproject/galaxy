import { fetcher } from "@/api/schema/fetcher";

export const getRemoteFiles = fetcher.path("/api/remote_files").method("get").create();
