import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

const LIMIT = 50;

export async function getDataset(query: string, historyId: string) {
    const { data, error } = await GalaxyApi().GET("/api/datasets", {
        params: {
            query: {
                history_id: historyId,
                q: ["name-contains"],
                qv: [query],
                offset: 0,
                limit: LIMIT,
            },
        },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function getDatasetCollection(query: string, historyId: string) {
    const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}/contents", {
        params: {
            path: {
                history_id: historyId,
            },
            query: {
                q: ["name-contains", "history_content_type-eq"],
                qv: [query, "dataset_collection"],
                offset: 0,
                limit: LIMIT,
                v: "dev",
                order: "hid",
            },
        },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function getInvocations() {
    const { data, error } = await GalaxyApi().GET("/api/invocations");
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function getJobs() {
    const { data, error } = await GalaxyApi().GET("/api/jobs");
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function getWorkflows() {
    const { data, error } = await GalaxyApi().GET("/api/workflows");
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function getHistories() {
    const { data, error } = await GalaxyApi().GET("/api/histories/published");
    if (error) {
        rethrowSimple(error);
    }
    return data;
}
