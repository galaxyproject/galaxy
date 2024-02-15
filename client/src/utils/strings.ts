/**
 * Converts an array of strings to a list, ending with "or"
 *
 * @example
 * // returns the string "a, b or c"
 * orList(["a", "b", "c"]);
 * @param items array of strings to join
 * @returns human readable comma + or separated list
 */
export function orList(items: string[]): string {
    if (items.length === 0) {
        return "";
    } else if (items.length === 1) {
        return items[0] as string;
    }

    return items
        .reverse()
        .flatMap((item, index) => {
            if (index === 0) {
                return [item, " or "];
            } else if (index !== 1) {
                return [", ", item];
            } else {
                return [item];
            }
        })
        .reverse()
        .join("");
}
