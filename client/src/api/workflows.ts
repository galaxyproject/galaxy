import { fetcher } from "@/api/schema";

export const workflowsFetcher = fetcher.path("/api/workflows").method("get").create();
