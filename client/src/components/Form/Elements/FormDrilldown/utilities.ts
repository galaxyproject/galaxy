export interface Option {
    name: string;
    value: string;
    leaf?: boolean;
    fullPath?: string;
    disabled?: boolean;
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

/**
 * Returns all types of "decendants" (child, grandchild, and so forth) in nested array (or null).
 * @param objects Array of Option objects with all keys intact
 * @returns values: string[]
 */
export function findDescendants(objects: Array<Option>, search: string): any[] | null {
    const stack: Array<Option> = [...objects];
    while (stack.length > 0) {
        const current = stack.pop();
        if (current === undefined) {
            return null;
        } else {
            if (current.value === search) {
                return current.options;
            }
            if (current.options && Array.isArray(current.options)) {
                stack.push(...current.options);
            }
        }
    }

    return null;
}

export function flattenValues(objects: any): string[] {
    const newArray = [];
    const stack = [...objects];

    while (stack.length > 0) {
        const current = stack.pop();
        if (current.value) {
            newArray.push(current.value);
        }
        if (current.options && Array.isArray(current.options)) {
            stack.push(...current.options);
        }
    }

    return newArray;
}
