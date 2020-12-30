import { pipe, Observable } from "rxjs";
import { switchMap, filter, share, shareReplay } from "rxjs/operators";

// feed observables, keyed by underlying database instance
export const feeds = new Map();

/**
 * Returns an observable with all the change events from the indicated database
 * @param {Observable} db$ Pouch database observable
 */
// prettier-ignore
export const changes = (cfg = {}) => {
    return pipe(
        switchMap((db) => {
            // console.log("subscribing to changes", db.name);
            if (!feeds.has(db)) {
                feeds.set(db, buildFeed(db, cfg));
            }
            return feeds.get(db);
        }),
        // filter out index creation which can appear as a change
        filter(({ id }) => !id.includes("_design")),
    );
};

/**
 * Creates an observable that emits changes to the indicated db instance
 * @param {PouchDB} db
 * @param {object} cfg
 */
const buildFeed = (db, cfg = {}) => {
    const { live = true, returnDocs = true, include_docs = true, since = "now", timeout = false } = cfg;

    const feed$ = new Observable((obs) => {
        // console.log("creating feed", db.name);
        const changeOpts = { live, include_docs, returnDocs, since, timeout };
        const feed = db.changes(changeOpts);
        feed.on("change", (update) => obs.next(update));
        feed.on("error", (err) => obs.error(err));
        return () => {
            // console.log("cancelling feed", db.name);
            feed.cancel();
        }
    });

    return feed$.pipe(share());
};
