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
