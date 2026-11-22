import type { StepInputDefaults } from "@/stores/workflowStepStore";

export interface FileDefault {
    class: "File";
    location: string;
    format?: string;
    [key: string]: unknown;
}

/** Keys describing the file at a specific location (dataset name, checksums). */
const LOCATION_BOUND_FILE_KEYS = ["basename", "created_from_basename", "MD5", "SHA-1", "SHA-256", "SHA-512"];

function isFileObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && (value as { class?: unknown }).class === "File";
}

export function isFileDefault(value: unknown): value is FileDefault {
    return isFileObject(value) && typeof value.location === "string";
}

export function defaultFileLocation(stepIn: StepInputDefaults | undefined): string {
    const value = stepIn?.input?.default;
    return isFileDefault(value) ? value.location : "";
}

/** Return a copy of a step's `in` with the `input` default pointing at `location`, or removed when empty. */
export function withDefaultFileLocation(stepIn: StepInputDefaults | undefined, location: string): StepInputDefaults {
    const inputs = { ...stepIn };
    location = location.trim();
    if (location) {
        const previous = inputs.input?.default;
        const file: Record<string, unknown> = isFileObject(previous) ? { ...previous } : {};
        if (file.location !== location) {
            for (const key of LOCATION_BOUND_FILE_KEYS) {
                delete file[key];
            }
        }
        const updated: FileDefault = { ...file, class: "File", location };
        inputs.input = { ...inputs.input, default: updated };
    } else if (inputs.input) {
        const { default: _default, ...rest } = inputs.input;
        if (Object.keys(rest).length) {
            inputs.input = rest;
        } else {
            delete inputs.input;
        }
    }
    return inputs;
}
