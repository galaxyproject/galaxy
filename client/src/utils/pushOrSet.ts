/**
 * Pushes a value to an array in an object, if the array exists. Else creates a new array containing value.
 * @param object Object which contains array
 * @param key Key which array is in
 * @param value Value to push
 */
export function pushOrSet<T, K extends string | number | symbol>(object: { [_key in K]: Array<T> }, key: K, value: T) {
    if (key in object) {
        object[key]!.push(value);
    } else {
        object[key] = [value];
    }
}
