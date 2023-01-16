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
