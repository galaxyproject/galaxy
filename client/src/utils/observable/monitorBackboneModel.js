import { Observable } from "rxjs";

export function monitorBackboneModel(sourceModel, prop) {
    return new Observable((obs) => {
        const evtName = `change:${prop}`;
        const changeHandler = (model) => obs.next(model);
        sourceModel.on(evtName, changeHandler);
        return () => {
            sourceModel.off(evtName, changeHandler);
        }
    });
}
