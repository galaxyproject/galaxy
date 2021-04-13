import { SearchParams } from "../../model";

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

// dumb math util
export const clamp = (val, [bottom, top]) => {
    return Math.max(bottom, Math.min(top, val));
};

// simple comparators
export const isDefined = (val) => {
    return val !== null && val !== undefined;
};

// defined, number and finite
export const isValidNumber = (val) => {
    return isDefined(val) && !isNaN(val) && isFinite(val);
};

export const paginationEqual = (a, b) => {
    return a.offset == b.offset && a.limit == b.limit;
};

/**
 * Creates limit/offset from scroll position and data set size, adds padding. This pagination is
 * used for the server-side content query where limit/offset will work
 *
 * @param   {float}  cursor         0-1 value representing how far down the list we are
 * @param   {int}    totalMatches   total server-side known matches for content query result
 * @param   {int}    pageSize       scaling parameter, number of rows in a "page"
 *
 * @return  {object}           limit/offset for use in content query
 */
export function buildPaginationWindow(cursor, totalMatches = 0, pageSize = SearchParams.pageSize) {
    // this is the offset that the cursor is pointed at if we're estimating
    const targetRow = Math.round(cursor * totalMatches);

    // overlap one page before and one page after, 3 total pages queried
    const offset = Math.max(0, targetRow - pageSize);
    const limit = 3 * pageSize;

    return { offset, limit, targetRow };
}
