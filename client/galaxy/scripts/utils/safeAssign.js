// Object.assign, but props transferred must exist in target

export function safeAssign(target, source = {}) {
    if (!(source instanceof Object)) {
        console.warn("safeAssign expected an object, instead got:", source);
        source = {};
    }
    Object.keys(source)
        .filter(prop => target.hasOwnProperty(prop))
        .forEach(prop => target[prop] = source[prop]);
}
