import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export async function addFavorite(userId, toolId) {
    const url = `${getAppRoot()}api/users/${userId}/favorites/tools`;
    try {
        const { data } = await axios.put(url, { object_id: toolId });
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function removeFavorite(userId, toolId) {
    const url = `${getAppRoot()}api/users/${userId}/favorites/tools/${encodeURIComponent(toolId)}`;
    try {
        const { data } = await axios.delete(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
