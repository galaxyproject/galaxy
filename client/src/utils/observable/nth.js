import { map } from "rxjs/operators";

// picks nth item of a combined array source
export const nth = (index = 0) => map((inputs) => inputs[index]);
