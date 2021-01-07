import { fromEvent } from "rxjs";
import { map, pluck } from "rxjs/operators";

export function monitorBackboneModel(sourceModel) {
    return fromEvent(sourceModel, "change").pipe(
        map(([model]) => model),
        pluck("attributes")
    );
}
