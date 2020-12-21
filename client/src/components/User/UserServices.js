import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { getGalaxyInstance } from "app";

export function getRecentInvocations() {
    const Galaxy = getGalaxyInstance();
    const params = { user_id: Galaxy.user.id, limit: 30, view: "collection" };
    const url = `${getAppRoot()}api/invocations`;
    return axios.get(url, { params: params });
}
