import { getAppRoot } from "onload/loadConfig";
import { copy } from "utils/clipboard";

export function copyLink(toolId, message) {
    const link = `${window.location.origin + getAppRoot()}root?tool_id=${toolId}`;
    // Encode the link to handle special characters in tool id
    copy(encodeURI(link), message);
}

export function copyId(toolId, message) {
    copy(toolId, message);
}

export function downloadTool(toolId) {
    window.location.href = `${getAppRoot()}api/tools/${toolId}/download`;
}

export function openLink(url) {
    window.open(url);
}

export function allowCachedJobs(userPreferences) {
    if (userPreferences && "extra_user_preferences" in userPreferences) {
        const extra_user_preferences = JSON.parse(userPreferences.extra_user_preferences);
        const keyCached = "use_cached_job|use_cached_job_checkbox";
        const hasCachedJobs = keyCached in extra_user_preferences;
        return hasCachedJobs ? ["true", true].includes(extra_user_preferences[keyCached]) : false;
    } else {
        return false;
    }
}
