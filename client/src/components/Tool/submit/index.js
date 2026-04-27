import * as Sentry from "@sentry/vue";

import { useConfigStore } from "@/stores/configurationStore";

import { submitToolJob as submitAsync } from "./submitAsync";
import { submitToolJob as submitLegacy } from "./submitLegacy";

export async function submitToolJob(params) {
    const configStore = useConfigStore();
    const celeryEnabled = !!configStore.config?.enable_celery_tasks;
    const hasParameters = !!params.formConfig?.has_parameters;
    if (celeryEnabled && hasParameters) {
        return submitAsync(params);
    }
    if (celeryEnabled && !hasParameters) {
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
