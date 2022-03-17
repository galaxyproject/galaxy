import { pipe } from "rxjs";
import { map, mergeMap } from "rxjs/operators";
import { ajax } from "rxjs/ajax";
import { prependPath } from "utils/redirect";

export const fetchDatasetById = () => {
    return pipe(
        map((id) => prependPath(`/api/datasets/${id}`)),
        mergeMap((url) => ajax.getJSON(url))
    );
};

export const fetchDatasetCollectionById = () => {
    return pipe(
        map((id) => prependPath(`/api/dataset_collections/${id}?instance_type=history`)),
        mergeMap((url) => ajax.getJSON(url))
    );
};

export const fetchInvocationStepById = () => {
    return pipe(
        map((id) => prependPath(`/api/invocations/any/steps/${id}`)),
        mergeMap((url) => ajax.getJSON(url))
    );
};
