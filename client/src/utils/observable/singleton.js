import { of, pipe, isObservable } from "rxjs";
import { map, mergeMap } from "rxjs/operators";

// retrieves a map key for the storage from the passed input
const defaultKeyFn = (val) => val;

// stores singleton products
const defaultStorage = new Map();

/**
 * Similar to map, but a unique output product value is created for each
 * individual input value.
 *
 * @param {Function} factory Create single output from unique input
 * @param {Map} storage Stores rendered product value
 * @param {Function} keyFn Optional, determines storage key from passed value
 */
export const singleton = (factory, storage = defaultStorage, keyFn = defaultKeyFn) =>
    pipe(
        map((val) => {
            const key = keyFn(val);
            return storage.has(key) ? storage.get(key) : storage.set(key, factory(val)).get(key);
        })
    );

/**
 * Generates a unique value from input source, then subscribes to that value if
 * it's an observable, or renders to an observable of one value if not.
 *
 * @param {Function} factory Create single output from unique input
 * @param {Map} storage Stores rendered product value
 * @param {Function} keyFn Optional, determines storage key from passed value
 */
export const singletonMap = (factory, storage, keyFn) =>
    pipe(
        singleton(factory, storage, keyFn),
        mergeMap((val) => (isObservable(val) ? val : of(val)))
    );
