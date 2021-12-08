import { of, race, pipe, concat, iif } from "rxjs";
import { filter, map, mergeMap, switchMap, delay, share, repeat, take, takeWhile } from "rxjs/operators";
import { cacheContent, monitorContentQuery, loadHistoryContents } from "components/providers/History/caching";
import { fetchDatasetById, fetchDatasetCollectionById, fetchInvocationStepById } from "./fetch";

// prettier-ignore
export const datasetMonitor = (cfg = {}) => {
    // delay gives the monitor a head-start so it can
    // spin up a little before we decide to do an ajax call
    const { spinUpDelay } = cfg;

    return pipe(
        switchMap((id) => createContentMonitor(id, 'dataset', spinUpDelay))
    );
};

export const datasetCollectionMonitor = (cfg = {}) => {
    const { spinUpDelay } = cfg;
    return pipe(switchMap((id) => createContentMonitor(id, "dataset_collection", spinUpDelay)));
};

const createContentMonitor = (id, contentType, spinUpDelay = 250) => {
    let fetcher;
    switch (contentType) {
        case "dataset":
            fetcher = fetchDatasetById;
            break;
        case "dataset_collection":
            fetcher = fetchDatasetCollectionById;
            break;
        default:
            console.error(`Can't create monitor for ${contentType}-${id}`);
    }
    return createMonitor(id, contentType, fetcher, spinUpDelay);
};

const buildPouchRequest = (id, contentType) => {
    return {
        selector: {
            id: { $eq: id },
            history_content_type: contentType,
        },
    };
};

// prettier-ignore
const createMonitor = (id, contentType, fetcher, spinUpDelay = 250) => {
    // build the pouchdb/mongo request, which is a selector
    // and limits, offsets, etc
    const request = buildPouchRequest(id, contentType);

    // retrieve changes from cache
    const changes$ = of(request).pipe(
        monitorContentQuery(),
        // singleUpdateResult(),
        filter(change => change.match && change.doc),
        map(change => change.doc),
        share()
    );

    // cache results that reflect non-deleted existing data in the cache
    const existing$ = changes$.pipe(
        filter(Boolean),
    );

    // load and cache dataset from server then switch over to the monitor
    const fetchItem$ = of(id).pipe(
        delay(spinUpDelay),
        fetcher(),
        mergeMap((rawJson) => cacheContent(rawJson, true))
    );

    // let the monitor and the ajax call race, first one wins
    const firstValue$ = race(fetchItem$, existing$).pipe(take(1));

    return concat(firstValue$, changes$);
};

const TERMINAL_JOB_STATES = ["ok", "error", "deleted", "paused"];
const stepIsTerminal = (step) => {
    const isTerminal =
        ["scheduled", "cancelled", "failed"].includes(step.state) &&
        step.jobs.every((job) => TERMINAL_JOB_STATES.includes(job.state));
    return isTerminal;
};

const createInvocationStepMonitor = (id, monitorEvery = 3000) => {
    const initialFetch$ = of(id).pipe(fetchInvocationStepById());
    const pollingFetch$ = of(id).pipe(
        delay(monitorEvery),
        fetchInvocationStepById(),
        repeat(),
        // takeWhile cancels source on true, so also cancels repeat
        takeWhile((val) => !stepIsTerminal(val), true)
    );
    return initialFetch$.pipe(
        // poll only if initial status is non-terminal. If polling, concat the initial result we already have
        // with pollingFetch$ which emits after the delay
        mergeMap((val) => iif(() => stepIsTerminal(val), of(val), concat(of(val), pollingFetch$)))
    );
};

export const invocationStepMonitor = (monitorEvery = 3000) =>
    pipe(switchMap((id) => createInvocationStepMonitor(id, monitorEvery)));

// feed observables, keyed by history id. Keeps just one historyMonitor around.
export const historyFeeds = new Map();

export const getHistoryMonitor = (historyId, monitorEvery = 3000) => {
    if (!historyFeeds.has(historyId)) {
        historyFeeds.set(historyId, buildHistoryMonitor(historyId, monitorEvery));
    }
    return historyFeeds.get(historyId);
};

// prettier-ignore
export const buildHistoryMonitor = (historyId, monitorEvery = 3000) => {
    // temporary hack until we can subscribe to invocations and their outputs.
    // set large windowSize around which to monitor (could we just monitor all updates?)
    const windowSize = 100000;
    return of([historyId, {showHidden: true, showVisible: true}, 1]).pipe(
        // noInitial skips fetching exisiting datasets and only monitors
        // for updated datastes after the last query (or now, if this is the first query)
        loadHistoryContents({windowSize, noInitial: true}),
        delay(monitorEvery),
        repeat(),
        share());
};

export const monitorHistoryUntilTrue = (condition, historyId, monitorEvery = 3000) => {
    // monitorHistory until condition is true, then fetch one last update
    const historyMonitor$ = getHistoryMonitor(historyId, monitorEvery);
    const primaryHistoryMonitor$ = historyMonitor$.pipe(
        takeWhile(() => !condition()),
        share()
    );
    return concat(
        primaryHistoryMonitor$,
        historyMonitor$.pipe(
            // get one more update after invocation is terminal
            take(1)
        )
    );
};
