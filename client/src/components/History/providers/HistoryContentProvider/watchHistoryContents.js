import { of } from "rxjs";
import { map } from "rxjs/operators";
import { aggregateCacheUpdates } from "../ContentProvider";
import { monitorHistoryContent } from "components/providers/History/caching";
import { SEEK } from "components/providers/History/caching/enums";
import { SearchParams } from "../../model";

// prettier-ignore
export const watchHistoryContents = (cfg = {}) => hid$ => {
    const { 
        history, 
        filters = new SearchParams(),
        pageSize = SearchParams.pageSize, 
        debug = false,
        keyField = "hid",
        keyDirection = SEEK.DESC,
        ...otherConfig 
    } = cfg;
    
    // builds a monitor observable based on a hid
    const monitor = (hid) => of([history.id, filters, hid]).pipe(
        monitorHistoryContent({ pageSize, debug, keyField })
    );

    // handles the plumbing for observing the query (monitor) and collecting the output into an
    // aggregate ordered list focused around the current target key (hid in this case)
    return hid$.pipe(
        map(val => parseInt(val)),
        aggregateCacheUpdates(monitor,  {
            keyField,
            keyDirection,
            pageSize, 
            debug,
            ...otherConfig 
        }),
    );
};
