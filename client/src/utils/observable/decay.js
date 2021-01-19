// Stateful delay gets longer with each repeated call
import { of } from "rxjs";
import { mergeMap, delay } from "rxjs/operators";

// prettier-ignore
export const decay = (cfg = {}) => {
    const {
        initialInterval,
        maxInterval = 60 * 1000,
        lambda = 0.25
    } = cfg;

    if (undefined === initialInterval) {
        throw new Error("provide an initialInterval to decay");
    }

    let counter = 0;

    return mergeMap(val => {
        let waitTime = Math.floor(initialInterval * Math.exp(lambda * counter++));
        waitTime = Math.max(waitTime, initialInterval);
        waitTime = Math.min(waitTime, maxInterval);
        // console.log("decay time", waitTime);
        return of(val).pipe(delay(waitTime))
    });
}
