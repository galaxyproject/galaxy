/**
 * Generic config storage object
 */

export function buildConfig(defaultConfigs = {}) {
    let storage = Object.assign({}, defaultConfigs);

    return new Proxy(storage, {
        get(target, propName) {
            if (propName in target) {
                return target[propName];
            } else {
                console.warn("Requested missing config prop", propName);
            }
        }
    });
}
