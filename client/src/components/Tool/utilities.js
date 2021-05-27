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

export function send(options, job_def) {
    const $f = $("<form/>").attr({
        action: options.action,
        method: options.method,
        enctype: options.enctype,
    });
    Object.entries(job_def.inputs).forEach(([value, key]) => {
        $f.append($("<input/>").attr({ name: key, value: value }));
    });
    $f.hide().appendTo("body").submit().remove();
}
