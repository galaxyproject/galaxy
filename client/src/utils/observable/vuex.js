/**
 * Function that creates on observable to watch a vuex store when provided a selector function.
 */

import { Observable } from "rxjs";

export function watchVuexSelector(store, selector, watchOptions = {}) {
    const { immediate = true } = watchOptions;

    return new Observable((observer) => {
        const callback = (result) => observer.next(result);
        return store.watch(selector, callback, { immediate });
    });
}
