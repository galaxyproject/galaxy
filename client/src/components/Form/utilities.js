import { getAppRoot } from "onload/loadConfig";
import { copy } from "utils/clipboard";

export function copyLink(toolId) {
    copy(`${window.location.origin + getAppRoot()}root?tool_id=${toolId}`, "Link was copied to your clipboard");
}

export function downloadTool(toolId) {
    window.location.href = `${getAppRoot()}api/tools/${toolId}/download`;
}

export function openLink(url) {
    window.open(url);
}
