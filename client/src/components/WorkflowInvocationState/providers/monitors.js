import { of, race, pipe, concat } from "rxjs";
import { filter, mergeMap, switchMap, delay, share, take } from "rxjs/operators";
// import { tag } from "rxjs-spy/operators/tag";
import { cacheContent, monitorContentQuery } from "components/History/caching";
import { singleUpdateResult } from "components/History/caching/db/monitorQuery";
import { fetchDatasetById } from "./fetch";

// prettier-ignore
export const datasetMonitor = (cfg = {}) => {
    // delay gives the monitor a head-start so it can
    // spin up a little before we decide to do an ajax call
    const { spinUpDelay } = cfg;

    return pipe(
        switchMap((id) => createDatasetMonitor(id, spinUpDelay))
    );
};

// prettier-ignore
const createDatasetMonitor = (id, spinUpDelay = 250) => {
    // build the pouchdb/mongo request, which is a selector
    // and limits, offsets, etc
    const pouchRequest = {
        selector: {
            id: { $eq: id },
        },
        // limit: 1
    };

    // retrieve changes from cache
    const changes$ = of(pouchRequest).pipe(
        monitorContentQuery(),
        singleUpdateResult(),
        share()
    );

    // cache results that reflect non-deleted existing data in the cache
    const existing$ = changes$.pipe(filter(Boolean));

    // load and cache dataset from server then switch over to the monitor
    const fetchDataset$ = of(id).pipe(
        delay(spinUpDelay),
        fetchDatasetById(),
        mergeMap((rawJson) => cacheContent(rawJson, true))
    );

    // let the monitor and the ajax call race, first one wins
    const firstValue$ = race(fetchDataset$, existing$).pipe(take(1));

    return concat(firstValue$, changes$);
};
