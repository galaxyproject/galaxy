import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

import { GalaxyApi } from "@/api";

export async function getDataset(query, historyId) {
    const { data, error } = await GalaxyApi().GET("/api/datasets", {
        params: {
            query: {
                history_id: historyId,
                q: ["name-contains"],
                qv: [query],
                offset: 0,
                limit: 50,
            },
        },
    });
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function getDatasetCollection(query, historyId) {
    const { data, error } = await GalaxyApi().GET("/api/histories/{id}/contents", {
        params: {
            path: {
                id: historyId,
            },
            query: {
                q: ["name-contains", "history_content_type-eq"],
                qv: [query, "dataset_collection"],
                offset: 0,
                limit: 50,
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
