import { fetcher } from "@/api/schema";

const getRoles = fetcher.path("/api/roles").method("get").create();
export async function getAllRoles() {
    const { data } = await getRoles({});
    return data;
}

export const deleteRole = fetcher.path("/api/roles/{id}").method("delete").create();
export const purgeRole = fetcher.path("/api/roles/{id}/purge").method("post").create();
export const undeleteRole = fetcher.path("/api/roles/{id}/undelete").method("post").create();
