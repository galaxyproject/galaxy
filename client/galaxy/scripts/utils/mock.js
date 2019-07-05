// console.log api but does nothing

const doNothing = () => null;

export const mock = source =>
    Object.keys(source)
        .filter(prop => typeof source[prop] == "function")
        .reduce((result, prop) => {
            result[prop] = doNothing;
            return result;
        }, {});
