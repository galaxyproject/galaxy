import { fetcher } from "@/api/schema/fetcher";

export const getDbKeys = fetcher.path("/api/genomes").method("get").create();
export const getRemoteFiles = fetcher.path("/api/remote_files").method("get").create();
