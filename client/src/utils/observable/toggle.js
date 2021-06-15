import { of, concat, EMPTY, NEVER } from "rxjs";
import { windowToggle, scan, switchAll } from "rxjs/operators";

// prettier-ignore
export const toggle = (toggleSrc$, startActive = true) => (src$) => {
    const init$ = startActive ? of(1) : EMPTY;
    const tgl$ = concat(init$, toggleSrc$).pipe(
        scan((acc) => !acc, true)
    );
    return src$.pipe(
        windowToggle(tgl$, (val) => (val ? src$ : NEVER)),
        switchAll()
    );
};
