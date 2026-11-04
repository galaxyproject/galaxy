import { format, parseISO } from "date-fns";

/** How a sub-workflow version panel names a workflow version, with markers such as "newest" in parentheses. */
export function workflowVersionText(
    version: { version: number; update_time: string; steps: number },
    markers: string[] = [],
): string {
    const date = format(parseISO(version.update_time), "MMM do yyyy");
    const suffix = markers.length ? ` (${markers.join(", ")})` : "";
    return `Version ${version.version + 1}: ${date}, ${version.steps} steps${suffix}`;
}
