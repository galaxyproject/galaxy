// Stateful delay gets longer with each repeated call
import { of } from "rxjs";
import { concatMap, delay } from "rxjs/operators";
import { show } from "utils/observable";

export const decay = (cfg = {}) => {
    const { initialInterval = 1000, maxInterval = 60 * 1000, lambda = 0.25, debug = false } = cfg;

    let counter = 0;

    return concatMap((val) => {
        let waitTime = Math.floor(initialInterval * Math.exp(lambda * counter++));
        waitTime = Math.max(waitTime, initialInterval);
        waitTime = Math.min(waitTime, maxInterval);

        return of(val).pipe(
            show(debug, (val) => console.log("decay", val, counter, waitTime)),
            delay(waitTime)
        );
    });
};
