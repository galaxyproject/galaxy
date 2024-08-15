import { type UnwrapNestedRefs } from "vue";

import { filterOptions } from "./filterOptions";
import { type SelectOption, type SelectValue, type UseSelectManyOptions, type UseSelectManyReturn } from "./selectMany";

export function main(options: UnwrapNestedRefs<UseSelectManyOptions>): UnwrapNestedRefs<UseSelectManyReturn> {
    const unselectedOptionsFiltered: SelectOption[] = [];
    const selectedOptionsFiltered: SelectOption[] = [];

    const filteredSelectOptions = filterOptions(options.optionsArray, options.filter, options.caseSensitive);

    const selectedValues = new Set(options.selected.map(stringifyObject));

    let moreUnselected = false;
    let moreSelected = false;

    for (let index = 0; index < filteredSelectOptions.length; index++) {
        const option = filteredSelectOptions[index]!;

        const value = stringifyObject(option.value);

        const isSelected = selectedValues.has(value);

        if (
            unselectedOptionsFiltered.length > options.unselectedDisplayCount &&
            selectedOptionsFiltered.length > options.selectedDisplayCount
        ) {
            break;
        }

        if (isSelected) {
            if (selectedOptionsFiltered.length < options.selectedDisplayCount) {
                selectedOptionsFiltered.push(option);
            } else {
                moreSelected = true;
            }
        } else {
            if (unselectedOptionsFiltered.length < options.unselectedDisplayCount) {
                unselectedOptionsFiltered.push(option);
            } else {
                moreUnselected = true;
            }
        }
    }

    return {
        unselectedOptionsFiltered,
        selectedOptionsFiltered,
        moreUnselected,
        moreSelected,
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
