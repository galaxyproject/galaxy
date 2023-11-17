import type { UnwrapNestedRefs } from "vue";

import type { SelectOption, SelectValue, UseSelectManyOptions, UseSelectManyReturn } from "./selectMany";

export function main(options: UnwrapNestedRefs<UseSelectManyOptions>): UnwrapNestedRefs<UseSelectManyReturn> {
    const unselectedOptionsFiltered: SelectOption[] = [];
    const selectedOptionsFiltered: SelectOption[] = [];

    let filteredSelectOptions: SelectOption[];
    let filterRegex: RegExp | undefined;

    if (options.asRegex) {
        try {
            filterRegex = new RegExp(options.filter, options.caseSensitive ? undefined : "i");
        } catch (e) {
            // ignore
        }
    }

    if (options.asRegex && filterRegex) {
        filteredSelectOptions = options.optionsArray.filter((option) => option.label.match(filterRegex!));
    } else if (options.caseSensitive) {
        filteredSelectOptions = options.optionsArray.filter((option) => option.label.includes(options.filter));
    } else {
        const filter = options.filter.toLowerCase();
        filteredSelectOptions = options.optionsArray.filter((option) => option.label.toLowerCase().includes(filter));
    }

    const selectedValues = options.selected.map(stringifyObject);

    for (let index = 0; index < filteredSelectOptions.length; index++) {
        const option = filteredSelectOptions[index]!;

        const value = stringifyObject(option.value);

        const isSelected = selectedValues.includes(value);

        if (isSelected && selectedOptionsFiltered.length < options.selectedDisplayCount) {
            selectedOptionsFiltered.push(option);
        } else if (unselectedOptionsFiltered.length < options.unselectedDisplayCount) {
            unselectedOptionsFiltered.push(option);
        }

        if (
            unselectedOptionsFiltered.length < options.unselectedDisplayCount &&
            selectedOptionsFiltered.length < options.selectedDisplayCount
        ) {
            break;
        }
    }

    return {
        unselectedOptionsFiltered,
        selectedOptionsFiltered,
    };
}

/**
 * Convert object to strings, leaving every other value unchanged
 * @param value
 * @returns
 */
function stringifyObject(value: SelectValue) {
    return typeof value === "object" && value !== null ? JSON.stringify(value) : value;
}
