import type { UnwrapNestedRefs } from "vue";

import { filterOptions } from "./filterOptions";
import type { SelectOption, SelectValue, UseSelectManyOptions, UseSelectManyReturn } from "./selectMany";

export function main(options: UnwrapNestedRefs<UseSelectManyOptions>): UnwrapNestedRefs<UseSelectManyReturn> {
    const unselectedOptionsFiltered: SelectOption[] = [];
    const selectedOptionsFiltered: SelectOption[] = [];

    let filterRegex: RegExp | undefined;

    if (options.asRegex) {
        try {
            filterRegex = new RegExp(options.filter, options.caseSensitive ? undefined : "i");
        } catch (e) {
            // ignore
        }
    }

    const filteredSelectOptions = filterOptions(
        options.optionsArray,
        options.filter,
        options.asRegex,
        options.caseSensitive,
        filterRegex
    );

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
            unselectedOptionsFiltered.length > options.unselectedDisplayCount &&
            selectedOptionsFiltered.length > options.selectedDisplayCount
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
