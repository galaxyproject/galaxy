/**
 * The path taken to drill into a subworkflow, carried in the editor URL.
 *
 * Each entry says "we were editing this workflow and opened this step of it". The entries are
 * ordered outermost first, so the last one is the workflow directly above the one being edited.
 * Keeping the whole path means the editor can offer a way back to any level, not just one up.
 */
export interface SubworkflowTrailEntry {
    /** Stored workflow id of the workflow that was left. */
    workflowId: string;
    /** order_index of the subworkflow step that was opened. */
    stepOrderIndex: number;
}

const ENTRY_SEPARATOR = ",";
const FIELD_SEPARATOR = ":";

export function encodeSubworkflowTrail(trail: SubworkflowTrailEntry[]): string {
    return trail.map((entry) => `${entry.workflowId}${FIELD_SEPARATOR}${entry.stepOrderIndex}`).join(ENTRY_SEPARATOR);
}

/** Malformed entries are dropped rather than thrown on, a hand edited URL should not break the editor. */
export function parseSubworkflowTrail(encoded?: string | null): SubworkflowTrailEntry[] {
    if (!encoded) {
        return [];
    }
    const trail: SubworkflowTrailEntry[] = [];
    for (const part of encoded.split(ENTRY_SEPARATOR)) {
        const [workflowId, rawStepOrderIndex] = part.split(FIELD_SEPARATOR);
        if (!workflowId || rawStepOrderIndex === undefined) {
            continue;
        }
        const stepOrderIndex = parseInt(rawStepOrderIndex, 10);
        if (Number.isNaN(stepOrderIndex)) {
            continue;
        }
        trail.push({ workflowId, stepOrderIndex });
    }
    return trail;
}
