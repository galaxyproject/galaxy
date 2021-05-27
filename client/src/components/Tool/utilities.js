import $ from "jquery";

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
