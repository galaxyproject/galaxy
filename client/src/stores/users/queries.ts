import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

export async function getCurrentUser() {
    const { data, error } = await GalaxyApi().GET("/api/users/{user_id}", {
        params: { path: { user_id: "current" } },
    });

    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function addFavoriteToolQuery(userId: string, toolId: string) {
    const { data, error } = await GalaxyApi().PUT("/api/users/{user_id}/favorites/{object_type}", {
        params: { path: { user_id: userId, object_type: "tools" } },
        body: { object_id: toolId },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data.tools;
}

export async function removeFavoriteToolQuery(userId: string, toolId: string) {
    const { data, error } = await GalaxyApi().DELETE("/api/users/{user_id}/favorites/{object_type}/{object_id}", {
        params: {
            path: {
                user_id: userId,
                object_type: "tools",
                object_id: toolId,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data.tools;
}

export async function setCurrentThemeQuery(userId: string, theme: string) {
    const { data, error } = await GalaxyApi().PUT("/api/users/{user_id}/theme/{theme}", {
        params: { path: { user_id: userId, theme } },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}
