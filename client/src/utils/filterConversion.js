import { defaultFilters } from "store/historyStore/model/filtering";

/** Check if all default options are set to default values */
export function containsDefaults(filterSettings) {
    const normalized = getDefaults();
    let hasDefaults = true;
    for (const key in normalized) {
        const value = String(filterSettings[key]).toLowerCase();
        const normalizedValue = String(normalized[key]).toLowerCase();
        if (value !== normalizedValue) {
            hasDefaults = false;
            break;
        }
    }
    return hasDefaults;
}

/** Normalize defaults by adding the operator to the key identifer */
export function getDefaults() {
    const normalized = {};
    Object.entries(defaultFilters).forEach(([key, value]) => {
        normalized[`${key}:`] = value;
    });
    return normalized;
}

/** Build a text filter from filter settings */
export function getFilterText(filterSettings) {
    // prepare defaults
    const normalized = getDefaults();
    const hasDefaults = containsDefaults(filterSettings);

    // build new filter text
    let newFilterText = "";
    Object.entries(filterSettings).forEach(([key, value]) => {
        const skipDefault = hasDefaults && normalized[key] !== undefined;
        if (!skipDefault && value !== undefined && value !== "") {
            if (newFilterText) {
                newFilterText += " ";
            }
            if (String(value).includes(" ")) {
                value = `'${value}'`;
            }
            newFilterText += `${key}${value}`;
        }
    });
    return newFilterText;
}
