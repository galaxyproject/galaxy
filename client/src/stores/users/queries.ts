import axios from "axios";
import { GalaxyApi } from "@/api";
import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

export type FavoriteObjectTypeValue = "tools" | "tags" | "edam_operations" | "edam_topics";

export interface FavoriteOrderEntry {
    object_type: FavoriteObjectTypeValue;
    object_id: string;
}

export interface FavoriteSummary {
    tools: string[];
    tags: string[];
    edam_operations: string[];
    edam_topics: string[];
    order: FavoriteOrderEntry[];
}

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

    return data as FavoriteSummary;
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

    return data as FavoriteSummary;
}

export async function addFavoriteTagQuery(userId: string, tag: string) {
    const { data, error } = await GalaxyApi().PUT("/api/users/{user_id}/favorites/{object_type}", {
        params: { path: { user_id: userId, object_type: "tags" } },
        body: { object_id: tag },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as FavoriteSummary;
}

export async function removeFavoriteTagQuery(userId: string, tag: string) {
    const { data, error } = await GalaxyApi().DELETE("/api/users/{user_id}/favorites/{object_type}/{object_id}", {
        params: {
            path: {
                user_id: userId,
                object_type: "tags",
                object_id: tag,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as FavoriteSummary;
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

export async function addFavoriteEdamOperationQuery(userId: string, operationId: string) {
    const { data, error } = await GalaxyApi().PUT("/api/users/{user_id}/favorites/{object_type}", {
        params: { path: { user_id: userId, object_type: "edam_operations" } },
        body: { object_id: operationId },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as FavoriteSummary;
}

export async function removeFavoriteEdamOperationQuery(userId: string, operationId: string) {
    const { data, error } = await GalaxyApi().DELETE("/api/users/{user_id}/favorites/{object_type}/{object_id}", {
        params: {
            path: {
                user_id: userId,
                object_type: "edam_operations",
                object_id: operationId,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as FavoriteSummary;
}

export async function addFavoriteEdamTopicQuery(userId: string, topicId: string) {
    const { data, error } = await GalaxyApi().PUT("/api/users/{user_id}/favorites/{object_type}", {
        params: { path: { user_id: userId, object_type: "edam_topics" } },
        body: { object_id: topicId },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as FavoriteSummary;
}

export async function removeFavoriteEdamTopicQuery(userId: string, topicId: string) {
    const { data, error } = await GalaxyApi().DELETE("/api/users/{user_id}/favorites/{object_type}/{object_id}", {
        params: {
            path: {
                user_id: userId,
                object_type: "edam_topics",
                object_id: topicId,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as FavoriteSummary;
}

export async function updateFavoriteOrderQuery(userId: string, order: FavoriteOrderEntry[]) {
    try {
        const { data } = await axios.put(`${getAppRoot()}api/users/${userId}/favorites/order`, {
            order,
        });
        return data as FavoriteSummary;
    } catch (error) {
        rethrowSimple(error);
        throw error;
    }
}
