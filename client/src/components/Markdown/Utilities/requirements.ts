import type { WorkflowLabel } from "@/components/Markdown/Editor/types";

import REQUIREMENTS from "./requirements.yml";

export function getRequiredLabels(name: string | undefined) {
    switch (getRequiredObject(name)) {
        case "history_dataset_id":
            return ["input", "output"];
        case "history_dataset_collection_id":
            return ["input", "output"];
        case "job_id":
            return ["step"];
    }
    return [];
}

export function getRequiredObject(name: string | undefined) {
    if (name) {
        for (const [key, values] of Object.entries(REQUIREMENTS)) {
            if (Array.isArray(values) && values.includes(name)) {
                return key !== "none" ? key : null;
            }
        }
    }
    return null;
}

export function hasValidLabel(name: string | undefined, args: Record<string, string>, labels: Array<WorkflowLabel>) {
    const requiredLabels = getRequiredLabels(name);
    if (labels !== undefined && requiredLabels.length > 0) {
        return requiredLabels.some((key) => {
            const value = args[key];
            return value && labels.some((label) => label.type === key && label.label === value);
        });
    }
    return true;
}

export function hasValidName(name: string | undefined) {
    if (name) {
        for (const values of Object.values(REQUIREMENTS)) {
            if (Array.isArray(values) && values.includes(name)) {
                return true;
            }
        }
    }
    return false;
}
