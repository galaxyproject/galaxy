import axios from "axios";

import type { ToolFormConfig } from "@/api/tools";
import type { FormData } from "@/components/Form/composables/useFormState";
import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

export interface UpdateToolFormDataOptions {
    offset: number;
    limit: number;
    search: string | undefined;
}
export type OptionsPagination = Record<string, Record<string, UpdateToolFormDataOptions>>;

interface GetToolFormDataRequest {
    tool_id?: string;
    tool_uuid?: string;
    tool_version?: string;
    history_id?: string;
    job_id?: string;
}
export interface UpdateToolFormDataRequest extends GetToolFormDataRequest {
    inputs?: FormData;
    options_pagination?: OptionsPagination;
}

/** Update tool form data on the server and return the updated form config. */
export async function updateToolFormData(payload: UpdateToolFormDataRequest): Promise<ToolFormConfig> {
    const url = `${getAppRoot()}api/tools/${payload.tool_id || payload.tool_uuid}/build`;
    try {
        const { data } = await axios.post(url, payload);
        return data as ToolFormConfig;
    } catch (e) {
        rethrowSimple(e);
    }
}

/** Tools data request helper **/
export async function getToolFormData(payload: GetToolFormDataRequest): Promise<ToolFormConfig> {
    let url = "";
    const data: Record<string, string> = {};

    // build request url and collect request data
    if (payload.job_id) {
        url = `${getAppRoot()}api/jobs/${payload.job_id}/build_for_rerun`;
    } else {
        url = `${getAppRoot()}api/tools/${payload.tool_id}/build`;
        const queryString = window.location.search;
        const params = new URLSearchParams(queryString);
        for (const [key, value] of params.entries()) {
            if (key != "tool_id") {
                data[key] = value;
            }
        }
    }
    payload.history_id && (data["history_id"] = payload.history_id);
    payload.tool_version && (data["tool_version"] = payload.tool_version);
    payload.tool_uuid && (data["tool_uuid"] = payload.tool_uuid);

    // attach data to request url
    if (Object.entries(data).length != 0) {
        const params = new URLSearchParams(data);
        url = `${url}?${params.toString()}`;
    }

    // request tool data
    try {
        const { data } = await axios.get(url);
        return data as ToolFormConfig;
    } catch (e) {
        rethrowSimple(e);
    }
}
