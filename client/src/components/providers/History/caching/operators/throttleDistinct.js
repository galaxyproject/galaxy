// same behavior as as utils/observable/throttleDistinct,
// but uses external state storage so we can put it in nested switchMaps, etc.

import moment from "moment";
import { pipe } from "rxjs";
import { filter } from "rxjs/operators";
import { createDateStore } from "../../model/DateStore";

export const throttleDistinctDateStore = createDateStore("throttleDistinct default");

// prettier-ignore
export const throttleDistinct = (config = {}) => {
    const {
        timeout = 1000,
        dateStore = throttleDistinctDateStore
    } = config;

    return pipe(
        filter((val) => {
            const now = moment();
            let ok = true;
            if (dateStore.has(val)) {
                const lastRequest = dateStore.get(val);
                ok = now - lastRequest > timeout;
            }
            if (ok) {
                dateStore.set(val, now);
            }
            return ok;
        })
    );
};
