// dumb formatter
export function cssLength(str, unit = "px") {
    if (str == null || str === "") {
        return undefined;
    } else if (isNaN(+str)) {
        return String(str);
    } else {
        const val = Number(str);
        return `${val}${unit}`;
    }
}

// validator
export function notNegative(rawVal) {
    const val = Number(rawVal);
    if (isNaN(val)) return false;
    if (val < 0) return false;
    return true;
}
