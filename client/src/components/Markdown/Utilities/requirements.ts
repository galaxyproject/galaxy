import REQUIREMENTS from "./requirements.yml";

export function isValidName(name: string | undefined) {
    if (name) {
        for (const values of Object.values(REQUIREMENTS)) {
            if (Array.isArray(values) && values.includes(name)) {
                return true;
            }
        }
    }
    return false;
}

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
