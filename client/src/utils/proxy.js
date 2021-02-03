/**
 * Diagnostic/debugging utility
 * Creates a generic proxy around an arbitrary target to watch
 * access to properties and functions.
 * @param {str} label console.log prefix label
 * @param {*} target Anything you want to watch
 */
export function genericProxy(label, target) {
    return new Proxy(target, {
        has() {
            console.log(`${label} -> has`, ...arguments);
            return Reflect.has(...arguments);
        },
        get() {
            console.log(`${label} -> get`, ...arguments);
            return Reflect.get(...arguments);
        },
        set() {
            console.log(`${label} -> set`, ...arguments);
            return Reflect.set(...arguments);
        },
        deleteProperty() {
            console.log(`${label} -> deleteProperty`, ...arguments);
            return Reflect.deleteProperty(...arguments);
        },
        apply() {
            console.log(`${label} -> apply`, ...arguments);
            return Reflect.apply(...arguments);
        },
        construct() {
            console.log(`${label} -> construct`, ...arguments);
            return Reflect.construct(...arguments);
        },
    });
}
