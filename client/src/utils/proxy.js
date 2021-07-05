/**
 * Diagnostic/debugging utility
 * Creates a generic proxy around an arbitrary target to watch
 * access to properties and functions.
 * @param {*} target Anything you want to watch
 * @param {str} label console.log prefix label
 */
export function loggingProxy(target, label = "proxy") {
    const methods = [
        "apply",
        "construct",
        "defineProperty",
        "get",
        "getOwnPropertyDescriptor",
        "getPrototypeOf",
        "has",
        "isExtensible",
        "ownKeys",
        "preventExtensions",
        "set",
        "setPrototypeOf",
    ];

    const handlerConfig = methods.reduce((handler, method) => {
        handler[method] = function () {
            console.groupCollapsed(`${label}:${method}`);
            const args = Array.from(arguments).slice(1);
            args.forEach((arg) => console.log(arg));
            console.groupEnd();
            return Reflect[method](...arguments);
        };
        return handler;
    }, {});

    return new Proxy(target, handlerConfig);
}
