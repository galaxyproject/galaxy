import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { copy } from "utils/clipboard";

export function copyLink(toolId, message) {
    copy(`${window.location.origin + getAppRoot()}root?tool_id=${toolId}`, message);
}

export function downloadTool(toolId) {
    window.location.href = `${getAppRoot()}api/tools/${toolId}/download`;
}

export function openLink(url) {
    window.open(url);
}
