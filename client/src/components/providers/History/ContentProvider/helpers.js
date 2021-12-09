import { SearchParams } from "components/providers/History/SearchParams";

// match object props
export const propMatch = (name) => (a, b) => {
    return a[name] === b[name];
};

// comparator for distinct() style operators inputs are an array of [id, SearchParams]
export const inputsSame = ([a0, a1], [b0, b1]) => {
    return a0 == b0 && SearchParams.equals(a1, b1);
};

// inputs + hid/cursor comparison
export const loadInputsSame = ([inputsA, cursorA], [inputsB, cursorB]) => {
    return cursorA == cursorB && inputsSame(inputsA, inputsB);
};

export const paginationEqual = (a, b) => {
    return a.offset == b.offset && a.limit == b.limit;
};

// debugging func for looking at abbreviated payload output
export const reportPayload = (p, keyField = "hid") => {
    const { contents = [], ...theRest } = p;
    const keys = contents.map((o) => o[keyField]);
    return { keys, ...theRest };
};
