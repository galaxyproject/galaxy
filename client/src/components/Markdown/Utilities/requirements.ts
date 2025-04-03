import type { WorkflowLabel } from "@/components/Markdown/Editor/types";

import REQUIREMENTS from "./requirements.yml";

export function getRequiredLabels(objectType: string | null) {
    switch (objectType) {
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

export function hasValidLabel(
    name: string | undefined,
    args: Record<string, string>,
    labels: Array<WorkflowLabel>
): boolean {
    const requiredObject = getRequiredObject(name);
    const requiredLabels = getRequiredLabels(requiredObject);
    if (labels !== undefined && requiredLabels.length > 0) {
        let matchCount = 0;
        for (const key of requiredLabels) {
            const value = args[key];
            if (value) {
                const matched = labels.some((label) => label.type === key && label.label === value);
                if (matched) {
                    matchCount++;
                }
            }
        }
        return matchCount === 1;
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

export function hasValidObject(name: string | undefined, args: Record<string, string>): boolean {
    const requiredObject = getRequiredObject(name);
    console.log(args);
    return !requiredObject || !!args[requiredObject];
}
