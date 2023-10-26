import { fetcher } from "@/schema"

const getUser = fetcher.path("/api/users/{user_id}").method("get").create();
const setTheme = fetcher.path("/api/users/{user_id}/theme/{theme}").method("put").create();
const addFavoriteTool = fetcher.path("/api/users/{user_id}/favorites/{object_type}").method("put").create();
const removeFavoriteTool = fetcher.path("/api/users/{user_id}/favorites/{object_type}/{object_id}").method("delete").create();

export async function getCurrentUser() {
    const response = await getUser({ user_id: "current" })
    if (response.status != 200) {
        throw new Error("Failed to get current user");
    }
    return response.data;
}

export async function addFavoriteToolQuery(userId: string, toolId: string) {
    const response = await addFavoriteTool({ user_id: userId, object_type: "tools", object_id: toolId })
    if (response.status != 200) {
        throw new Error("Failed to add tool to favorites");
    }
    return response.data["tools"];
}

export async function removeFavoriteToolQuery(userId: string, toolId: string) {
    const response = await removeFavoriteTool({ user_id: userId, object_type: "tools", object_id: toolId })
    if (response.status != 200) {
        throw new Error("Failed to remove tool from favorites");
    }
    return response.data["tools"];
}

export async function setCurrentThemeQuery(userId: string, theme: string) {
    const response = await setTheme({ user_id: userId, theme: theme })
    if (response.status != 200) {
        throw new Error("Failed to set theme");
    }
    return response.data;
}
