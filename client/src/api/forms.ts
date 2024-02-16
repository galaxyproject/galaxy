import { fetcher } from "@/api/schema";

export const deleteForm = fetcher.path("/api/forms/{id}").method("delete").create();
export const undeleteForm = fetcher.path("/api/forms/{id}/undelete").method("post").create();
