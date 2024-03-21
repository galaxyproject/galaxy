import axios from "axios";

import { type components, fetcher } from "@/api/schema";
import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

export type ShowFullJobResponse = components["schemas"]["ShowFullJobResponse"];

type ReportJobErrorPayload = components["schemas"]["ReportJobErrorPayload"];
const postErrorReport = fetcher.path("/api/jobs/{job_id}/error").method("post").create();
export async function sendErrorReport(job_id: string, payload: ReportJobErrorPayload) {
    try {
        const { data } = await postErrorReport({
            job_id,
            dataset_id: payload.dataset_id,
            email: payload.email,
            message: payload.message,
        });

        return data.messages;
    } catch (e) {
        rethrowSimple(e);
    }
}

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
