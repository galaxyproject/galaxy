import { fromEvent } from "rxjs";
import { map } from "rxjs/operators";

// prettier-ignore
export function monitorBackboneModel(sourceModel, evtName = "change") {
    return fromEvent(sourceModel, evtName).pipe(
        map(([model]) => model.toJSON())
    );
}
