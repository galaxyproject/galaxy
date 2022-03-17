// Object.assign, but props transferred must exist in target

export function safeAssign(target, source = {}) {
    if (!(source instanceof Object)) {
        console.warn("safeAssign expected an object, instead got:", source);
        source = {};
    }
    Object.keys(source)
        .filter((prop) => Object.prototype.hasOwnProperty.call(target, prop))
        .forEach((prop) => (target[prop] = source[prop]));
}

/**
 * Creates a reusable utility scrubber function that removes reserved initialization props from raw
 * which are already defined by Klass. This lets us just stick one model instance into.
 *
 * Ex: const scrubber = scrubModelProps(History); *
 *     const newHistory = new History(scrubber(oldHistory));
 */

export function scrubModelProps(Klass) {
    const restrictedKeys = new Set(Object.getOwnPropertyNames(Klass.prototype));

    return (raw = {}) => {
        const pairs = Object.entries(raw || {});
        return pairs.reduce((clean, [propName, val]) => {
            return restrictedKeys.has(propName) ? clean : { ...clean, [propName]: val };
        }, {});
    };
}
