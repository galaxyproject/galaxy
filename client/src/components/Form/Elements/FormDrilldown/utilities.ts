export interface Option {
    name: string;
    value: string;
    options: Array<Option>;
}

export type Value = string[] | string | null;

/**
 * Returns an array of values from nested drill down options provided
 * @param headOptions Array of options to get values from
 * @returns values: string[]
 */
export function getAllValues(headOptions: Array<Option>): string[] {
    let options = null;
    const values: string[] = [];
    const stack: Array<Array<Option>> = [headOptions];
    while ((options = stack.pop())) {
        options.forEach((option) => {
            if (option.value) {
                values.push(option.value);
            }
            if (option.options.length > 0) {
                stack.push(option.options);
            }
        });
    }
    return values;
}
