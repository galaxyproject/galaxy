export const sortByObjectProp = (propName) => (a, b) => {
    const aa = a[propName].toLowerCase();
    const bb = b[propName].toLowerCase();
    return bb - aa;
};
