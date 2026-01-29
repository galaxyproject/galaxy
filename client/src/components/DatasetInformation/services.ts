import axios from "axios";

import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

export async function setAttributes(datasetId: string, settings: object, operation: string) {
    const payload = {
        dataset_id: datasetId,
        operation: operation,
        ...settings,
    };

    const url = `${getAppRoot()}dataset/set_edit`;

    try {
        const { data } = await axios.put(url, payload);

        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
