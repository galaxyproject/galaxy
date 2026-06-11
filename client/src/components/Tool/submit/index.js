import * as Sentry from "@sentry/vue";

import { useConfigStore } from "@/stores/configurationStore";

import { submitToolJob as submitAsync } from "./submitAsync";
import { submitToolJob as submitLegacy } from "./submitLegacy";

export async function submitToolJob(params) {
    const configStore = useConfigStore();
    const toolRequestsEnabled = configStore.config?.enable_tool_requests !== false;
    const celeryEnabled = !!configStore.config?.enable_celery_tasks;
    const hasParameters = !!params.formConfig?.has_parameters;
    if (toolRequestsEnabled && celeryEnabled && hasParameters) {
        return submitAsync(params);
    }

    let fallbackReason;
    if (!toolRequestsEnabled) {
        fallbackReason = "enable_tool_requests is false";
    } else if (!celeryEnabled) {
        fallbackReason = "enable_celery_tasks is false";
    } else {
        fallbackReason = "tool has no typed parameters";
    }
    console.debug(`tool submission fell back to /api/tools (${fallbackReason}) for tool_id=${params.jobDef?.tool_id}`);

    if (toolRequestsEnabled && celeryEnabled && !hasParameters) {
        Sentry.captureMessage("tool submission fell back to /api/tools: no typed parameters", {
            level: "info",
            tags: {
                fallback_reason: "no_parameters",
                tool_id: params.jobDef?.tool_id,
            },
        });
    }
    return submitLegacy(params);
}
