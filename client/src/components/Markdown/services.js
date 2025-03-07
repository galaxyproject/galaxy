import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

import { GalaxyApi } from "@/api";

export async function copyCollection(hdcaId, historyId) {
    const url = `${getAppRoot()}api/histories/${historyId}/contents/dataset_collections`;
    const payload = {
        source: "hdca",
        type: "dataset_collection",
        content: hdcaId,
        copy_elements: true,
    };
    try {
        const { data } = await axios.post(url, payload);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
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
