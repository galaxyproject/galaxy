import { unref } from "vue";

import { useUid } from "./utils/uid";

/**
 * Allows for keying objects by their internal ids.
 * Returns a function which takes an object and returns a string uid.
 * Passing the same object to this function twice, will return the same id.
 *
 * Passing the same object to a function created by another
 * `useKeyedObjects` composable will not produce the same ids.
 *
 * A cloned object will not have the same id as the object it was cloned from.
 * Modifying an objects properties will not affect its id.
 *
 * @returns A function which allows for keying objects
 */
export function useKeyedObjects() {
    const keyCache = new WeakMap<object, string>();

    function keyObject(object: object) {
        const cachedKey = keyCache.get(object);

        if (cachedKey) {
            return cachedKey;
        } else {
            const key = unref(useUid("object-"));
            keyCache.set(object, key);
            return key;
        }
    }

    return { keyObject };
}
