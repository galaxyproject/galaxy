export const sortByObjectProp = (...propNames) => {
    const resolve = resolveProp(...propNames);
    return (a, b) => {
        const aa = resolve(a).toLowerCase();
        const bb = resolve(b).toLowerCase();
        return bb - aa;
    };
};

const resolveProp =
    (...propNames) =>
    (target) => {
        return propNames.reduce((src, propName) => {
            if (src === undefined) {
                return undefined;
            }
            return propName in src ? src[propName] : undefined;
        }, target);
    };
