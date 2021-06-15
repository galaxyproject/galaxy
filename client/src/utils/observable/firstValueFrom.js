import { take } from "rxjs/operators";

// take one emission, assume we're done, return as promise
// TODO: firstValueFrom will be native in rxjs soon as toPromise is being deprecated
export const firstValueFrom = (src$) => src$.pipe(take(1)).toPromise();
