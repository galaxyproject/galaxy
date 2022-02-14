/**
 * Similar to combineLatest but adds a small debounce to avoid a duplicate event
 * firing when multiple sources change at the same time.
 */

import { combineLatest } from "rxjs";
import { debounceTime } from "rxjs/operators";

export const whenAny = (...sources) => combineLatest(sources).pipe(debounceTime(0));
