import { SelectOption } from "./selectMany";

export function filterOptions(
    options: SelectOption[],
    filterString: string,
    asRegex: boolean,
    caseSensitive: boolean,
    filterRegex?: RegExp | null
) {
    let filteredSelectOptions;

    if (asRegex && filterRegex) {
        filteredSelectOptions = options.filter((option) => Boolean(option.label.match(filterRegex!)));
    } else if (caseSensitive) {
        filteredSelectOptions = options.filter((option) => option.label.includes(filterString));
    } else {
        const filter = filterString.toLowerCase();
        filteredSelectOptions = options.filter((option) => option.label.toLowerCase().includes(filter));
    }

    return filteredSelectOptions;
}
