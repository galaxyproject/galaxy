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
