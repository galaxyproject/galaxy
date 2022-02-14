import { pipe } from "rxjs";
import { map } from "rxjs/operators";

/**
 * passing objects into the worker removes class information, Pass in an array
 * of constructors to be assigned, in order of the input array.
 */
// prettier-ignore
export const hydrate = (constructors = []) => pipe(
    map((inputs) => {
        return inputs.map((rawInput, i) => {
            const C = constructors[i];
            return C ? new C(rawInput) : rawInput;
        });
    })
)
