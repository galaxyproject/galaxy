import { fetcher } from "@/schema/fetcher";

export const getDatatypes = fetcher.path("/api/datatypes").method("get").create();
export const getGenomes = fetcher.path("/api/genomes").method("get").create();
export const getRemoteFiles = fetcher.path("/api/remote_files").method("get").create();
