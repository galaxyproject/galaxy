import { type SelectOption } from "./selectMany";

export function filterOptions(options: SelectOption[], filter: string | RegExp, caseSensitive: boolean) {
    let filteredSelectOptions;

    if (filter instanceof RegExp) {
        filteredSelectOptions = options.filter((option) => Boolean(option.label.match(filter)));
    } else if (caseSensitive) {
        filteredSelectOptions = options.filter((option) => option.label.includes(filter));
    } else {
        const filterLowercase = filter.toLowerCase();
        filteredSelectOptions = options.filter((option) => option.label.toLowerCase().includes(filterLowercase));
    }

    return filteredSelectOptions;
}
