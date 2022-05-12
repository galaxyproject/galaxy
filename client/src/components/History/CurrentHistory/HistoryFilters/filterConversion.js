import { defaultFilters } from "store/historyStore/model/filtering";

/** Normalize defaults by adding the operator to the key identifer */
export function defaultsNormalized() {
    const normalized = {};
    Object.entries(defaultFilters).forEach(([key, value]) => {
        normalized[`${key}=`] = value;
    });
    return normalized;
}

/** Check if all default options are set to default values */
export function containsDefaults(filterSettings) {
    const normalized = defaultsNormalized();
    let hasDefaults = true;
    for (const key in normalized) {
        const value = filterSettings[key];
        if (value !== normalized[key]) {
            hasDefaults = false;
            break;
        }
    }
    return hasDefaults;
}

/** Build a text filter from filter settings */
export function getFilterText(filterSettings) {
    const normalized = defaultsNormalized();
    const hasDefaults = containsDefaults(filterSettings);
    // build new filter text
    let newFilterText = "";
    Object.entries(filterSettings).forEach(([key, value]) => {
        const skipDefault = hasDefaults && normalized[key] !== undefined;
        if (!skipDefault && value !== undefined) {
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