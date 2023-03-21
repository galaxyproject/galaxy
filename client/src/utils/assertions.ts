/**
 * Asserts that a value is not undefined or null
 * @param value value to test
 * @param errorMessage optional error message
 */
export function assertDefined<T>(value: T, errorMessage?: string): asserts value is NonNullable<T> {
    if (value === undefined || value === null) {
        const message = errorMessage ?? `Value is undefined or null`;
        throw message;
    }
}

/**
 * Asserts that a value is not undefined or null, then returns said value.
 * Can be used inline
 *
 * @param value value to test
 * @param errorMessage optional error message
 * @returns NonNullable value
 *
 * @see assertDefined
 */
export function ensureDefined<T>(value: T, errorMessage?: string): NonNullable<T> {
    assertDefined(value, errorMessage);
    return value;
}
