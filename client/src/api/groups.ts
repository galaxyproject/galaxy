import axios from "axios";

import { components, fetcher } from "@/api/schema";

type GroupModel = components["schemas"]["GroupModel"];
export async function getAllGroups(): Promise<GroupModel[]> {
    const { data } = await axios.get("/api/groups");
    return data;
}

export const deleteGroup = fetcher.path("/api/groups/{group_id}").method("delete").create();
export const purgeGroup = fetcher.path("/api/groups/{group_id}/purge").method("post").create();
export const undeleteGroup = fetcher.path("/api/groups/{group_id}/undelete").method("post").create();
