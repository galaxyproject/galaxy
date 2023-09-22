import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export async function sendErrorReport(dataset, message, email) {
    const payload = {
        dataset_id: dataset.id,
        message,
        email,
    };
    const url = `${getAppRoot()}api/jobs/${dataset.creating_job}/error`;
    try {
        const { data } = await axios.post(url, payload);
        return data.messages;
    } catch (e) {
        rethrowSimple(e);
    }
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
