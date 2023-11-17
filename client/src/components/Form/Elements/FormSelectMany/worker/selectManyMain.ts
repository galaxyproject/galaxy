import type { UnwrapNestedRefs } from "vue";

import type { SelectOption, UseSelectManyOptions, UseSelectManyReturn } from "./selectMany";

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

    const selectedValues = options.selected.map((value) => (typeof value === "object" ? JSON.stringify(value) : value));

    filteredSelectOptions.forEach((option) => {
        const value = typeof option.value === "object" ? JSON.stringify(option.value) : option.value;

        if (
            unselectedOptionsFiltered.length < options.unselectedDisplayCount ||
            selectedOptionsFiltered.length < options.selectedDisplayCount
        ) {
            const isSelected = selectedValues.includes(value);

            if (isSelected && selectedOptionsFiltered.length < options.selectedDisplayCount) {
                selectedOptionsFiltered.push(option);
            } else if (unselectedOptionsFiltered.length < options.unselectedDisplayCount) {
                unselectedOptionsFiltered.push(option);
            }
        }
    });

    return {
        unselectedOptionsFiltered,
        selectedOptionsFiltered,
    };
}
