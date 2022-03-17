// I'm actually unclear on why I needed this operator to make pouchdb
// observables work. This bears further investigation. To my knowledge
// withLatestFrom() does the same thing as this operator, yet this works and
// withLatestFrom() doesn't when used with pouchdb observable creation.

import { zip, of, pipe } from "rxjs";
import { concatMap } from "rxjs/operators";

// prettier-ignore
export const needs = (dep$) => pipe(
    concatMap((src) => zip(of(src), dep$))
);
