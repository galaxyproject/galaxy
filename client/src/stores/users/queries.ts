import axios from "axios";
import { prependPath } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

export async function getCurrentUser() {
    const url = prependPath("/api/users/current");
    const response = await axios.get(url);
    if (response.status != 200) {
        throw new Error("Failed to get current user");
    }
    return response.data;
}

export async function addFavoriteToolQuery(userId: string, toolId: string) {
    const url = prependPath(`/api/users/${userId}/favorites/tools`);
    try {
        const { data } = await axios.put(url, { object_id: toolId });
        return data["tools"];
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function removeFavoriteToolQuery(userId: string, toolId: string) {
    const url = prependPath(`/api/users/${userId}/favorites/tools/${encodeURIComponent(toolId)}`);
    try {
        const { data } = await axios.delete(url);
        return data["tools"];
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function setCurrentThemeQuery(userId: string, theme: string) {
    const url = prependPath(`/api/users/${userId}/theme/${theme}`);
    try {
        const { data } = await axios.put(url, { theme: theme });
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
