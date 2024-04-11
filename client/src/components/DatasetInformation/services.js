import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

import { jobsReportError } from "@/api/jobs";

export async function sendErrorReport(dataset, message, email) {
    const jobId = dataset.creating_job;
    const request = {
        job_id: jobId,
        dataset_id: dataset.id,
        message,
        email,
    };
    const { data } = await jobsReportError(request);
    return data.messages;
}

export async function setAttributes(datasetId, settings, operation) {
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
