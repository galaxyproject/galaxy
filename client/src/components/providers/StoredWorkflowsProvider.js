import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { cleanPaginationParameters } from "./utils";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";
import { rethrowSimple } from "utils/simple-error";

export function storedWorkflowsProvider(ctx, callback, extraParams = {}) {
    const { root, ...requestParams } = ctx;
    const apiUrl = `${root}api/workflows`;
    const cleanParams = cleanPaginationParameters(requestParams);
    const promise = axios.get(apiUrl, { params: { ...cleanParams, ...extraParams } });

    // Must return a promise that resolves to an array of items
    return promise.then((data) => {
        // Pluck the array of items off our axios response
        const items = data.data;
        callback && callback(data);
        // Must return an array of items or an empty array if an error occurred
        return items || [];
    });
}

async function storedWorkflowDetails({ storedWorkflowId }) {
    const url = `${getAppRoot()}api/workflows/${storedWorkflowId}`;
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export const StoredWorkflowDetailsProvider = SingleQueryProvider(storedWorkflowDetails);
