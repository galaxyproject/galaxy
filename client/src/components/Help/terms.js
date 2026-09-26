import terms from "./terms.yml";

export function hasHelp(uri) {
    const parts = uri.split(".");
    let rest = terms;
    for (const part of parts) {
        rest = rest[part];
        if (rest === undefined) {
            return false;
        }
    }
    return true;
}

export function help(uri) {
    const parts = uri.split(".");
    let rest = terms;
    for (const part of parts) {
        rest = rest[part];
    }
    return rest;
}
