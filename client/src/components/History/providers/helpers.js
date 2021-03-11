import { of, merge } from "rxjs";
import { mapTo, catchError } from "rxjs/operators";
import { SearchParams } from "../model";

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

// set true when input triggers, set false when output emits
export const isLoading = (input) => (output) => {
    const on = input.pipe(mapTo(true));
    const off = output.pipe(
        catchError(() => of(null)),
        mapTo(false)
    );
    return merge(on, off);
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

// scroll position exact match
// export const scrollPosEquals = (a, b) => {
//     return a.cursor === b.cursor && a.key === b.key;
// };

// validate output variables before rendering
// export const validPayload = ({ topRows, bottomRows, totalMatches }) => {
//     return isValidNumber(topRows) && isValidNumber(bottomRows) && isValidNumber(totalMatches);
// };
