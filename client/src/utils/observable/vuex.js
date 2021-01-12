/**
 * Operator that watches a vuex store when provided a source selector function
 * Output is an observable, source input should be the store.
 * Example:
 *   of(store).pipe(watchVuexSelector({ selector: yourFn }))
 */

import { Observable } from "rxjs";
import { switchMap } from "rxjs/operators";

export const watchVuexSelector = (config) => (store$) => {
    // Selector is a function that digs through the vuex state loooking
    // for the value you care about
    //    ex: state => state.user.currentUser

    const { selector, watchOptions = { immediate: true } } = config;

    return store$.pipe(
        switchMap((store) => {
            return new Observable((subscriber) => {
                const callback = (result) => subscriber.next(result);
                return store.watch(selector, callback, watchOptions);
            });
        })
    );
};
