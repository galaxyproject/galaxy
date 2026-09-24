import axios from "axios";

import { getAppRoot } from "@/onload/loadConfig";

export async function submitToolJob({ jobDef, formData }) {
    const legacyPayload = toLegacyPayload(jobDef, formData);
    const { data } = await axios.post(`${getAppRoot()}api/tools`, legacyPayload);
    return data;
}

function toLegacyPayload(jobDef, formData) {
    const inputs = { ...formData };
    if (jobDef.send_email_notification) {
        inputs["send_email_notification"] = true;
    }
    if (jobDef.rerun_remap_job_id !== undefined) {
        inputs["rerun_remap_job_id"] = jobDef.rerun_remap_job_id;
    }
    if (jobDef.use_cached_jobs) {
        inputs["use_cached_job"] = true;
    }
    const payload = {
        tool_id: jobDef.tool_id,
        tool_uuid: jobDef.tool_uuid,
        tool_version: jobDef.tool_version,
        history_id: jobDef.history_id,
        inputs,
    };
    if (jobDef.tags?.length) {
        payload.__tags = jobDef.tags;
    }
    if (jobDef.preferred_object_store_id) {
        payload.preferred_object_store_id = jobDef.preferred_object_store_id;
    }
    if (jobDef.data_manager_mode) {
        payload.data_manager_mode = jobDef.data_manager_mode;
    }
    if (jobDef.credentials_context) {
        payload.credentials_context = jobDef.credentials_context;
    }
    return payload;
}
