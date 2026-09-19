/**
 * Asserts that a value is not undefined or null
 * @param value value to test
 * @param error optional error message, or Error object
 */
export function assertDefined<T>(value: T, error?: string | Error): asserts value is NonNullable<T> {
    if (value === undefined || value === null) {
        const message = error ?? TypeError(`Value is undefined or null`);
        throw message instanceof Error ? message : TypeError(message);
    }
}

/**
 * Asserts that a value is not undefined or null, then returns said value.
 * Can be used inline
 *
 * @param value value to test
 * @param error optional error message, or Error object
 * @returns NonNullable value
 *
 * @see assertDefined
 */
export function ensureDefined<T>(value: T, error?: string | Error): NonNullable<T> {
    assertDefined(value, error);
    return value;
}

export function assertArray(value: unknown, error?: string | Error): asserts value is Array<unknown> {
    if (!(typeof value === "object" && Array.isArray(value))) {
        const message = error ?? TypeError(`Value is not an Array`);
        throw message instanceof Error ? message : TypeError(message);
    }
}
